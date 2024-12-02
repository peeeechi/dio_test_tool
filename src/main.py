import TkEasyGUI as sg
import threading
import time
import enum
import serial
import serial.tools
import serial.tools.list_ports
import re
import typing
import queue

# 定数定義
RECEIVE_PARSE_PATTERN = r'dio-(?P<input>[\d,]+)-(?P<output>[\d,]+)-end'
RECEIVE_PARSE_REGEX = re.compile(RECEIVE_PARSE_PATTERN)
serial_locker = threading.RLock()

DI_PORT_NUM = 8
DO_PORT_NUM = 8
DI_CAPTION = "Digital Input 現在値"
DO_CAPTION = "Digital Output 現在値"

# メッセージキューの作成
message_queue = queue.Queue()

class PinState(enum.IntEnum):
    off = 0
    on = 1

class AppState(object):
    def __init__(self):
        self.di_state = [PinState.off for _ in range(DI_PORT_NUM)]
        self.do_state = [PinState.off for _ in range(DO_PORT_NUM)]
        self.do_command = [PinState.off for _ in range(DO_PORT_NUM)]
        self.serial: typing.Optional[serial.Serial] = None

app_state = AppState()

def get_ports():
    return serial.tools.list_ports.comports()

def create_cmd(cmd_arr: typing.List[PinState]):
    cmd_str_arr = [str(c.value) for c in cmd_arr]
    return "command-" + ",".join(cmd_str_arr) + "-end\n"

def update_state():
    while True:
        # GUI更新用のデータをキューに送る
        connect_state = "接続" if app_state.serial is None else "切断"
        port_values = ["None", *[f'{port.device} ({port.description})' for port in get_ports()]]
        message_queue.put(('connect_btn', connect_state))
        message_queue.put(('serial_ports', port_values))

        if app_state.serial:
            line = ""
            with serial_locker:
                line = app_state.serial.readline().decode("utf-8")
            if line != "":
                try:
                    line = line.replace('\r','').replace('\n', '')
                    print("serial: ", f"'{line}'")
                    m = RECEIVE_PARSE_REGEX.search(line)
                    if m:
                        input_str_arr = m.groupdict()['input'].split(',')
                        output_str_arr = m.groupdict()['output'].split(',')
                        if len(input_str_arr) == DI_PORT_NUM:
                            app_state.di_state = [PinState.on if elm_str == "1" else PinState.off for elm_str in input_str_arr]
                        if len(output_str_arr) == DO_PORT_NUM:
                            app_state.do_state = [PinState.on if elm_str == "1" else PinState.off for elm_str in output_str_arr]
                        values = [
                            [DI_CAPTION, *["On" if v == PinState.on else "Off" for v in app_state.di_state]],
                            [DO_CAPTION, *["On" if v == PinState.on else "Off" for v in app_state.do_state]],
                        ]
                        message_queue.put(('state_table', values))
                except Exception as e:
                    print('invalid str received:')
                    print(e)

        # DOボタンの状態更新
        for i in range(DO_PORT_NUM):
            button_state = {
                'text': "Off" if app_state.do_command[i] == PinState.off else "On",
                'color': ('black', 'white') if app_state.do_command[i] == PinState.off else ('black', 'red'),
                'disabled': app_state.serial is None
            }
            message_queue.put(('do_button', (i, button_state)))

        time.sleep(0.1)  # スレッドの負荷軽減

class MainWindow:
    def __init__(self):
        # レイアウトからタイマーボタンを削除
        layout = [
            [sg.Combo(values=["None"], key='serial-ports', default_value="", size=(40, 1)),
             sg.Button(button_text="接続", key='connect-btn')],
            [sg.Text('Digital Out 指示値:')],
            [*[sg.Text(f"Port{i+1}", size=(6, 1)) for i in range(DO_PORT_NUM)]],
            [*[sg.Button(button_text="Off", key=f'do-btn{i}', disabled=True, size=(3, 1),
                        button_color=("black", "red")) for i in range(DO_PORT_NUM)]],
            [sg.Table([
                [DI_CAPTION, *["Off" for _ in range(DI_PORT_NUM)]],
                [DO_CAPTION, *["Off" for _ in range(DI_PORT_NUM)]],
            ], headings=["項目", *[f'Port{p+1}' for p in range(DO_PORT_NUM)]], key='state-table')]
        ]

        self.window = sg.Window('dio-ros-driver テスター', layout, finalize=True,
                              auto_size_text=True, element_padding=(10, 10))

    def check_queue(self):
        """キューのチェックと処理"""
        try:
            while True:  # キューの中身をすべて処理
                message_type, data = message_queue.get_nowait()
                
                if message_type == 'connect_btn':
                    self.window['connect-btn'].update(data)
                elif message_type == 'serial_ports':
                    self.window['serial-ports'].update(values=data)
                elif message_type == 'state_table':
                    self.window['state-table'].update(data)
                elif message_type == 'do_button':
                    i, state = data
                    self.window[f'do-btn{i}'].update(
                        text=state['text'],
                        button_color=state['color'],
                        disabled=state['disabled']
                    )
        except queue.Empty:
            pass

    def run(self):
        btn_keys = [f'do-btn{i}' for i in range(DO_PORT_NUM)]

        # 更新スレッドの開始
        threading.Thread(target=update_state, daemon=True).start()

        # イベントループ
        while True:
            event, values = self.window.read(timeout=100)  # タイムアウトを設定
            # print(event, values)

            # タイムアウトごとにキューをチェック
            if event == sg.TIMEOUT_KEY:
                self.check_queue()
                continue

            if event in btn_keys:
                do_btn_index = int(event.replace('do-btn', ''))
                btn_state = app_state.do_command[do_btn_index]
                app_state.do_command[do_btn_index] = (
                    PinState.on if btn_state == PinState.off else PinState.off)
                if app_state.serial:
                    cmd = create_cmd(app_state.do_command)
                    print('cmd:', cmd)
                    app_state.serial.write(cmd.encode('utf-8'))

            elif event == "connect-btn":
                if app_state.serial is None or not app_state.serial.is_open:
                    port = values['serial-ports']
                    if port not in ["None", '']:
                        port = port.split(' ')[0]
                        try:
                            with serial_locker:
                                app_state.serial = serial.Serial(
                                    port, baudrate=9600, parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE, timeout=3)
                                app_state.do_command = [PinState.off for _ in range(DO_PORT_NUM)]
                        except Exception as e:
                            print(e)
                else:
                    with serial_locker:
                        app_state.serial.close()
                        app_state.serial = None

            if event == sg.WIN_CLOSED:
                if app_state.serial is not None and app_state.serial.is_open:
                    with serial_locker:
                        app_state.serial.close()
                        app_state.serial = None
                break

        self.window.close()

if __name__ == '__main__':
    app = MainWindow()
    app.run()