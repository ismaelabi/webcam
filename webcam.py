import dash
from dash import html, Output, Input, dcc, ctx
import cv2
import threading
import time
from flask import Response, Flask

server = Flask(__name__)
app = dash.Dash(__name__, server=server)

# Global camera instance
camera = cv2.VideoCapture(0)
current_camera_index = 0

frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

is_recording = False
video_writer = None
lock = threading.Lock()

stopwatch_running = False
elapsed_seconds = 0

# MJPEG stream generator
def generate_frames():
    global is_recording, video_writer
    while True:
        success, frame = camera.read()
        if not success:
            break

        # Write to file if recording
        with lock:
            if is_recording and video_writer:
                video_writer.write(frame)

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # Stream it as MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Flask route for the video stream
@server.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Dash layout
app.layout = html.Div(style={'textAlign': 'center'}, children=[
    html.H2("Camera Interface"),

    html.Div([
        html.Div(id='stopwatch-display', children="00:00:00"),
        html.Button("Start", id='start-button', n_clicks=0),
        html.Button("Stop", id='stop-button', n_clicks=0),
        html.Button("Reset", id='reset-button', n_clicks=0),
        dcc.Interval(id='interval', interval=1000, n_intervals=0, disabled=True),
    ], style={'textAlign': 'center', 'margin': '20px'}),

    html.Div([
        html.Label("Select Camera:"),
        dcc.Dropdown(
            id="camera-select",
            options=[{"label": f"Camera {i}", "value": i} for i in range(3)],  # adjust based on number of cams
            value=0,
            style={"width": "200px"}
        )
    ], style={
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "marginBottom": "20px"
    }),


    html.Img(
        src="/video_feed",
        style={"width": f"{frame_width}px", "height": f"{frame_height}px", "border": "2px solid black"}),


    html.Div([
        html.Button("Take Picture", id="btn-picture", n_clicks=0),
        html.Button("Start/Stop Recording", id="btn-record", n_clicks=0, style={'marginLeft': '10px'}),
    ], style={'marginTop': '20px'}),

    html.Div(id='status-message', style={'marginTop': '20px', 'fontWeight': 'bold'})
])

@app.callback(
    Output('status-message', 'children'),
    Input('btn-picture', 'n_clicks'),
    Input('btn-record', 'n_clicks'),
    Input('camera-select', 'value'),
    prevent_initial_call=True
)
def handle_camera_actions(pic_clicks, rec_clicks, selected_camera):
    global camera, current_camera_index, is_recording, video_writer

    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "btn-picture":
        ret, frame = camera.read()
        if ret:
            filename = f"picture_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            return f"Picture saved as {filename}"

    elif trigger_id == "btn-record":
        if not is_recording:
            filename = f"recording_{int(time.time())}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 20.0
            width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            video_writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
            is_recording = True
            return "Recording started..."
        else:
            is_recording = False
            if video_writer:
                video_writer.release()
                video_writer = None
            return "Recording stopped and saved."

    elif trigger_id == "camera-select":
        if selected_camera == current_camera_index:
            return dash.no_update
        if camera.isOpened():
            camera.release()
        camera = cv2.VideoCapture(selected_camera)
        if not camera.isOpened():
            return f"Failed to open camera {selected_camera}"
        current_camera_index = selected_camera
        return f"Switched to camera {selected_camera}"

    return dash.no_update


@app.callback(
    Output('interval', 'disabled'),
    [Input('start-button', 'n_clicks'),
     Input('stop-button', 'n_clicks'),
     Input('reset-button', 'n_clicks')]
)
def control_stopwatch(start, stop, reset):
    global stopwatch_running, elapsed_seconds

    triggered = ctx.triggered_id

    if triggered == 'start-button':
        stopwatch_running = True
        return False  # Enable interval
    elif triggered == 'stop-button':
        stopwatch_running = False
        return True   # Disable interval
    elif triggered == 'reset-button':
        stopwatch_running = False
        elapsed_seconds = 0
        return True   # Disable interval

    return True  # Default state

@app.callback(
    Output('stopwatch-display', 'children'),
    Input('interval', 'n_intervals')
)
def update_stopwatch(n):
    global elapsed_seconds, stopwatch_running
    if stopwatch_running:
        elapsed_seconds += 1

    mins = elapsed_seconds // 60
    secs = elapsed_seconds % 60
    return f"{mins:02d}:{secs:02d}"

if __name__ == '__main__':
    try:
        app.run(debug=False)
    finally:
        camera.release()
        if video_writer:
            video_writer.release()
