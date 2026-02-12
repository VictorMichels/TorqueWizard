#!/usr/bin/env python3
import multiprocessing #Number 1 problem generator
import sys
import os
import webview
from starlette.formparsers import MultiPartParser
from serial.tools import list_ports
from nicegui import app, run, ui
from collections import deque
from datetime import datetime
import serial
import time
import math
import logging
import asyncio
import random
import plotly.graph_objects as go
import pandas as pd
import io
import csv
from io import StringIO

#Globals
ser = None
play_plot = None 
log_container = None
tabs = None 
auto_scroll = None
play_range = None
view_plot = None
connection_switch = None
port_select = None
baud_selecter = None
command_input = None

MAX_DISPLAY = 100
x_display = deque(maxlen=MAX_DISPLAY)
y_display = deque(maxlen=MAX_DISPLAY)
all_data = []

MultiPartParser.spool_max_size = 1024 * 1024 * 50 
SAMPLING_RATE = 80.0
PERIOD = 1.0 / SAMPLING_RATE
incoming_data_queue = deque()
logging.getLogger('pywebview').setLevel(logging.CRITICAL)
rainbow_colors = ['text-red-500', 'text-orange-500', 'text-yellow-500', 'text-green-500', 'text-blue-500', 'text-indigo-500', 'text-purple-500']
log_queue = deque() 
start_time = time.time()

# AppImage Image fix
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS                                # If running as a compiled exe, look in the PyInstaller temp folder
else:
    base_path = os.path.dirname(os.path.abspath(__file__))  # If running as a script, look in the current directory
assets_path = os.path.join(base_path, 'assets')             # Construct the absolute path to the assets folder

# PLOT SETUP
view_fig = go.Figure()
view_fig.update_layout(
    title="Data Analysis",
    template="plotly_white",
    margin=dict(l=50, r=20, t=50, b=50),
    xaxis=dict(title="Time [s]"),
    yaxis=dict(title="Force [mN]")
)

play_fig = go.Figure(data=[go.Scatter(x=[], y=[], mode='lines')])
play_fig.update_layout(
    title="Play Analysis",
    template="plotly_white",
    margin=dict(l=50, r=20, t=50, b=50),
    xaxis=dict(title="Time [s]"),
    yaxis=dict(title="Force [mN]")
)

# HELPER FUNCTIONS
def extract_int(s):
    digits = ''.join([c for c in s if c == '-' or c.isdigit()])
    if not digits: return None
    try: return int(digits)
    except ValueError: return None

def get_ports():
    return [p.device for p in list_ports.comports()]

def toggle_connection():
    global ser
    if connection_switch.value:
        try:
            ser = serial.Serial(port_select.value, baudrate=baud_selecter.value, timeout=0.1)
            ui.notify(f'Connected to {port_select.value}', type='positive')        
        except Exception as e:
            ui.notify(f'Could not connect: {e}', type='negative')
            connection_switch.value = False 
    else:
        if ser:
            ser.close()
            ser = None
        ui.notify('Disconnected')

def send_command():
    if ser and ser.is_open:
        cmd = f'{command_input.value}\n'.encode()
        ser.write(cmd)
        command_input.value = ''
    else:
        ui.notify('Not connected!', type='warning')

def reset_connection():
    if connection_switch and connection_switch.value:
        ui.notify("Connection lost due to change in Baud/Port", type='info')
        connection_switch.value=False

def clear_log():
    log_container.clear()

async def download_csv():
    with StringIO() as buffer:
        writer = csv.writer(buffer)
        for i, (_, value) in enumerate(all_data, start=1):
            writer.writerow([i, value])
        csv_content = buffer.getvalue()

    if app.native.main_window:
        file_selection = await app.native.main_window.create_file_dialog(
            dialog_type=30, 
            directory='/', 
            save_filename='play_analysis_data.csv'
        )
        if file_selection:
            destination_path = file_selection[0] if isinstance(file_selection, (list, tuple)) else file_selection
            try:
                with open(destination_path, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                ui.notify(f'Saved to {destination_path}', type='positive')
            except Exception as e:
                ui.notify(f'Error saving file: {e}', type='negative')
    else:
        ui.download(csv_content.encode('utf-8'), 'play_analysis_data.csv')

async def handle_upload(e):
    try:
        filename = e.file.name
        content = e.file.read()
        if hasattr(content, '__await__'):
            content = await content
        df = pd.read_csv(io.BytesIO(content), header=None)
        force = df.iloc[:, 1] 
        y_time = [i * PERIOD for i in range(len(force))]

        view_fig.data = []
        view_fig.add_trace(go.Scatter(x=y_time, y=force, mode='lines', name='Force'))
        view_fig.update_layout(title=f"File: {filename} ({len(force)} samples)")
        if view_plot:
            view_plot.update()
        
        ui.notify(f"Loaded {filename} successfully!")
    except Exception as err:
        ui.notify(f"Error: {str(err)}", type='negative')


# Fast (80 Hz)
async def read_serial_loop():
    while True:
        if ser and ser.is_open and ser.in_waiting:
            try:
                raw_line = ser.readline().decode('utf-8', errors='replace')
                log_queue.append(raw_line)
                clean_line = raw_line.strip()
                val = extract_int(clean_line)
                
                # Check if UI is ready (play_range might be None during startup)
                if val is not None and play_range:
                    try:
                        limit = int(play_range.value)
                        if val > limit: val = limit
                        elif val < -limit: val = -limit
                    except:
                        pass # Ignore conversion errors temporarily
                    
                    t_now = time.time() - start_time
                    all_data.append((t_now, val))
                    incoming_data_queue.append((t_now, val))
                    
            except Exception as e:
                print(f"Serial Exception: {e}")
        await asyncio.sleep(0)

# Slow (10 Hz)
async def update_ui_loop():
    while True:
        # Check if UI elements are initialized
        if tabs and play_plot and log_container: 
            while incoming_data_queue:
                t, val = incoming_data_queue.popleft()
                x_display.append(t)
                y_display.append(val)
            
            # Play Plot
            if str(tabs.value) == '2' and len(x_display) > 0:
                play_plot.figure.data[0].x = list(x_display)
                play_plot.figure.data[0].y = list(y_display)
                play_plot.update()
            
            # Serial Monitor log
            if str(tabs.value) == '4' and log_queue:
                text_batch = "".join(log_queue)
                text_batch = text_batch.rstrip()
                log_queue.clear()
                with log_container:
                    ui.label(text_batch).classes('font-mono leading-none py-0 p-0 gap-0').style('white-space: pre-wrap')
                
                if auto_scroll and auto_scroll.value:
                    log_container.scroll_to(percent=1.0)
            elif str(tabs.value) != '4' and log_queue:
                log_queue.clear()

        await asyncio.sleep(0.1)#i.e. 10Hz

async def start_loops():
    asyncio.create_task(read_serial_loop())
    asyncio.create_task(update_ui_loop())
    
@ui.page('/') 
def index():
    app.add_static_files('/static', assets_path)
    #Using global to link the UI elements created here to the background loops
    global play_plot, log_container, tabs, auto_scroll, play_range 
    global view_plot, connection_switch, port_select, baud_selecter, command_input

    with ui.dialog() as dialog3, ui.card():
        #Main title
        with ui.row().classes('w-full justify-center mb-2'):
            ui.label('Tutorial').classes('text-4xl font-bold')
        ui.separator().classes('mb-4')

        #Main Menu
        with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
            with ui.card_section():
                ui.label('Main Menu').classes('text-2xl font-bold text-blue-600 mb-2')
                ui.label('This page is your starting point, it introduces the software and lets you navigate to all its key features.')\
                    .classes('text-lg text-gray-700 leading-relaxed')

        #Play
        with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
            with ui.card_section():
                ui.label('Play').classes('text-2xl font-bold text-green-600 mb-2')
                ui.label('This is where you can record and export into a .csv the graph traced by all the Force vectors over time.')\
                    .classes('text-lg text-gray-700 leading-relaxed')

        #View
        with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
            with ui.card_section():
                ui.label('View').classes('text-2xl font-bold text-purple-600 mb-2')
                ui.label('View allows you to ')\
                    .classes('text-lg text-gray-700 leading-relaxed inline')
                ui.label('view').classes('text-lg font-bold text-purple-600 mx-1 inline')
                ui.label(' the whole graph that you recorded previously by importing a .csv.')\
                    .classes('text-lg text-gray-700 leading-relaxed inline')

    #    #Calibration
    #    with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
    #        with ui.card_section():
    #            ui.label('Calibrate').classes('text-2xl font-bold text-orange-600 mb-2')
    #            ui.label('Set different weights as calibration, by default it\'s set to 500 grams.')\
    #                .classes('text-lg text-gray-700 leading-relaxed')

        #Serial Monitor
        with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
            with ui.card_section():
                ui.label('Serial Monitor').classes('text-2xl font-bold text-red-600 mb-2')
                ui.label('Essentially a debugger for your serial connection, this should be your first step to use this software.')\
                    .classes('text-lg text-gray-700 leading-relaxed')

        #Credits
        with ui.card().tight().classes('w-full hover:shadow-lg transition-shadow duration-300'):
            with ui.card_section():
                ui.label('Credits').classes('text-2xl font-bold text-indigo-600 mb-2')
                ui.label('Credits and acknowledgments for the software development.')\
                    .classes('text-lg text-gray-700 leading-relaxed')
        ui.button('Close', on_click=dialog3.close)

    with ui.button(icon='help', color='primary',on_click=dialog3.open).props('fab').classes('fixed bottom-4 right-4 z-50'):
        ui.element().props('aria-label="Open help menu"')  
    
    with ui.header().classes(replace='row items-center') as header:
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white size=lg')

    with ui.left_drawer().classes('bg-blue-100 items-center') as left_drawer:
        ui.label('Torque Wizard').classes('text-3xl font-bold')
        ui.separator()
        with ui.tabs().props('vertical inline-label').classes('w-full') as tabs:
            with ui.tab('1', label="").classes('!justify-start'):
                with ui.row().classes('items-center'):
                    ui.icon('dashboard').props('size=lg')
                    ui.label('Main Menu').classes('text-lg font-bold')
            with ui.tab('2', label="").classes('!justify-start'):
                with ui.row().classes('items-center'):
                    ui.icon('play_arrow').props('size=lg')
                    ui.label('Play').classes('text-lg font-bold')
            with ui.tab('3', label="").classes('!justify-start'):
                with ui.row().classes('items-center'):
                    ui.icon('visibility').props('size=lg')
                    ui.label('View').classes('text-lg font-bold')
            with ui.tab('4', label="").classes('!justify-start'):
                with ui.row().classes('items-center'):
                    ui.icon('usb').props('size=lg')
                    ui.label('Serial Monitor').classes('text-lg font-bold')
            with ui.tab('5', label="").classes('!justify-start'):
                with ui.row().classes('items-center'):
                    ui.icon('sentiment_satisfied_alt').props('size=lg')
                    ui.label('Credits').classes('text-lg font-bold')

    with ui.tab_panels(tabs, value='1').classes('w-full'):
        with ui.tab_panel('1'):
            with ui.column().classes('items-center w-full'):
                ui.label('Main Menu').classes('text-5xl font-bold text-center w-full mb-2')
                with ui.row().classes('items-center gap-1'):
                    ui.label('Welcome to ').classes('text-3xl text-center ')
                    with ui.row().classes('items-center gap-0'):
                        word = "TorqueWizard"
                        for i, letter in enumerate(word):
                            color_class = rainbow_colors[i % len(rainbow_colors)]
                            ui.label(letter).classes(f'text-4xl font-bold {color_class}')
                    ui.label('!').classes('text-3xl text-center')
                ui.label('Start by configuring your Serial with Serial Monitor!').classes('text-xl')
                ui.image('/static/no_background1.png').classes('w-128 h-auto mx-auto z-0')

        with ui.tab_panel('2'):
            ui.label('Play').classes('text-5xl font-bold text-center w-full')
            with ui.row().classes('w-full items-center justify-evenly'):
                ui.button('Record into CSV', on_click=download_csv, icon='save').classes('text-xl font-bold text-center')
                play_range = ui.input(label='Absolute Range', placeholder='This must be a number', value=30000).classes('text-xl font-bold')
            play_plot = ui.plotly(play_fig).classes('w-full h-[60vh]')

        with ui.tab_panel('3'):
            ui.label('View').classes('text-5xl font-bold text-center w-full')
            with ui.card().classes('w-full p-4'):
                ui.upload(on_upload=handle_upload, auto_upload=True).classes('w-full mb-4')
                view_plot = ui.plotly(view_fig).classes('w-full h-96')

        with ui.tab_panel('4'):
            ui.label('Serial Monitor').classes('text-5xl font-bold text-center w-full')
            with ui.row().classes('w-full items-center'):
                baud_rates=[600,1200,2400,4800,9600,14400,19200,28800,38400,57600,115200,230400]
                baud_selecter = ui.select(options=baud_rates, on_change=reset_connection, label='Baud Rates', value=115200).classes('w-50 mr-16')
                port_select = ui.select(get_ports(), on_change=reset_connection, label='Select Port', value=None).classes('w-50 mr-8')
                ui.button(icon='refresh', on_click=lambda: port_select.set_options(get_ports())).props('flat round')
                connection_switch = ui.switch('Connect', on_change=toggle_connection)
            
            with ui.row().classes('w-full items-center'):
                command_input = ui.input('Send command').classes('w-full')
                command_input.on('keydown.enter', send_command)
            
            with ui.row().classes('w-full items-center'):
                auto_scroll = ui.switch('Auto-scroll', value=True)
                ui.button('Clear', icon='clear', on_click=clear_log).props('flat')
            
            log_container = ui.scroll_area().classes('w-full h-128 bg-gray-100 rounded border')

        with ui.tab_panel('5'):
            ui.label('Credits').classes('text-5xl font-bold text-center w-full')
            with ui.dialog().classes('w-screen h-screen bg-black/90') as dialog1:
                with ui.card().classes('w-full h-full bg-transparent border-none shadow-none p-4'):
                    ui.button(icon='close', on_click=dialog1.close)
                    ui.image('/static/me_solar.jpeg')
            with ui.dialog().classes('w-screen h-screen bg-black/90') as dialog2:
                with ui.card().classes('w-full h-full bg-transparent border-none shadow-none p-4'):
                    ui.button(icon='close', on_click=dialog2.close)
                    ui.image('/static/aero.jpeg').classes('max-h-[80vh] max-w-[80vw] object-contain')

            with ui.column().classes('items-center w-full'):
                with ui.row().classes('items-center'):
                    ui.button('Developed by:', on_click=dialog1.open)
                    ui.button('Developed to:', on_click=dialog2.open)
                with ui.row().classes('items-center gap-1'):
                    ui.label('Based on this')
                    ui.label('fantastic').classes('font-bold italic font-[Comic_Sans_MS]')
                    ui.label('idea:')
                ui.image('/static/plano.png').classes('w-full max-w-4xl h-auto mx-auto')

# EXECUTION BLOCK
if __name__ in {"__main__", "__mp_main__"}:
    multiprocessing.freeze_support()            #Prevent recursion
    app.native.window_args['maximized'] = True  #Setup window
    app.on_startup(start_loops)                 #Start background tasks cleanly
    ui.run(
        native=True, 
        window_size=(1280, 1024), 
        title="TorqueWizard",
        reload=False
    )