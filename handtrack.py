import mediapipe as mp
import cv2 as cv
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()

PROXY_HM_ADDRESS = os.getenv("PROXY_HM_ADDRESS")
PROXY_HMIP_ADDRESS = os.getenv("PROXY_HMIP_ADDRESS")

proxy_hm = xmlrpc.client.ServerProxy(PROXY_HM_ADDRESS)
proxy_hmip = xmlrpc.client.ServerProxy(PROXY_HMIP_ADDRESS)

circle_id = None
pointer_cooldown = 0
lights = [False, False]
shutter = False
click_holddown = 0

debug = False

camera = cv.VideoCapture(0)

mp_hands = mp.solutions.hands
mp_drawing_styles = mp.solutions.drawing_styles
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
        model_complexity = 0,
        min_detection_confidence = 0.5,
        min_tracking_confidence = 0.5)

def update_pointerpos(image):
    global circle_id, pointer_cooldown, lights, click_holddown, debug, shutter

    image.flags.writeable = False
    image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
    results = hands.process(image)
        
    image.flags.writeable = True
    image = cv.cvtColor(image, cv.COLOR_RGB2BGR)
        
    if results.multi_hand_landmarks:
        hand_zero = results.multi_hand_landmarks[0]
        index = hand_zero.landmark[8]
        thumb = hand_zero.landmark[4]
        
        indices = [0, 1, 2, 5, 9, 13, 17]
        center_x = sum(hand_zero.landmark[i].x for i in indices) / len(indices)
        center_y = sum(hand_zero.landmark[i].y for i in indices) / len(indices)
                    
        h, w, c = image.shape
                    
        ix = int(index.x * w)
        iy = int(index.y * h)
        iz = int(index.z * w)
        tx = int(thumb.x * w)
        ty = int(thumb.y * h)
        tz = int(thumb.z * w)
        cx = int(center_x * w)
        cy = int(center_y * h)
        
        scrx = int(center_x * screen_width)
        scry = int(center_y * screen_height)
        
        dist = math.sqrt((ix-tx)**2+(iy-ty)**2+(iz-tz)**2)
            
        r = 40
        if dist <= 30:

            color = (0, 255, 0, 128)

            if click_holddown > 0:
                click_holddown -= 1
                pointer_cooldown = 20

            if is_hovered(scrx, scry, r) == "button_Schreibtisch":
                if click_holddown == 0:
                    click_holddown = 30
                if click_holddown == 1:
                    if lights[0] == False:
                        lights[0] = True
                        update_real_light("Schreibtisch", True)
                    else:
                        lights[0] = False
                        update_real_light("Schreibtisch", False)

            if is_hovered(scrx, scry, r) == "button_Bett":
                if click_holddown == 0:
                    click_holddown = 30
                if click_holddown == 1:
                    if lights[1] == False:
                        lights[1] = True
                        update_real_light("Bett", True)
                    else:
                        lights[1] = False
                        update_real_light("Bett", False)

            if is_hovered(scrx, scry, r) == "button_Rollo":
                            if click_holddown == 0:
                                click_holddown = 30
                            if click_holddown == 1:
                                if shutter == False:
                                    shutter = update_real_shutter(0.0)
                                else:
                                    shutter = update_real_shutter(1.0)
        else:
            click_holddown = 0
            if is_hovered(scrx, scry, r) in ["button_Rollo", "button_Bett", "button_Schreibtisch"]:
                color = (87, 185, 255, 128)
            else:
                color = (255, 0, 0, 128)
                    
        if pointer_cooldown > 0:
            pointer_cooldown -= 1
    
        if circle_id is None:
            tk_circle_img = create_pointer(r, color)
            canvas.image_ref = tk_circle_img
            circle_id = canvas.create_image(scrx-r, scry-r, image=tk_circle_img, anchor="nw")
        else:
            canvas.coords(circle_id, scrx-r, scry-r)   
            tk_circle_img = create_pointer(r, color)
            canvas.image_ref = tk_circle_img
            canvas.itemconfig(circle_id, image=tk_circle_img)
    else:
        tk_circle_img = ImageTk.PhotoImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
        canvas.image_ref = tk_circle_img
        canvas.itemconfig(circle_id, image=tk_circle_img)

    if debug == True:
        print("x: " + str(scrx) + ", y:" + str(scry))
    
    update_bg()
    window.after(1, evaluate_camera)

def evaluate_camera():
    if camera.isOpened():
            success, image = camera.read()
            if not success:
                print("Empty frame")
            else:
                update_pointerpos(image)

def exit_program(e):
    camera.release()
    window.destroy()

def create_pointer(r, color):
    circle_img = Image.new("RGBA", (2*r, 2*r), (0, 0, 0, 0))
    draw = ImageDraw.Draw(circle_img)
    
    outer_color = (color[0], color[1], color[2], color[3] // 2)
    draw.ellipse([0, 0, 2*r, 2*r], fill=outer_color)
    
    border = 12
    draw.ellipse([border, border, 2*r - border, 2*r - border], fill=color)
    return ImageTk.PhotoImage(circle_img)

def is_hovered(scrx, scry, r):
    if scrx in range(1200-r, 1200+r) and scry in range(500-r, 500+r):
        return "button_Schreibtisch"
    if scrx in range(1400-r, 1400+r) and scry in range(800-r, 800+r):
        return "button_Bett"
    if scrx in range(1100, 1300) and scry in range(700, 1000):
        return "button_Rollo"
    
def update_bg():
        state = (lights[0], lights[1], shutter)
        canvas.itemconfig(bg_id, image=bg_images[state])

BETT_ID = os.getenv("BETT_ID")
SCHREIBTISCH_ID = os.getenv("SCHREIBTISCH_ID")

def update_real_light(light_id, state):
    global proxy_hmip

    light_id_dic = {
        "Bett": BETT_ID,
        "Schreibtisch": SCHREIBTISCH_ID,
    }

    proxy_hmip.setValue(light_id_dic[light_id], "STATE", state)
    print("Licht " + str(light_id) + " wird auf " + str(state) + " gesetzt")

def get_real_light():
    global proxy_hmip

    light_id_dic = {
            "Bett": BETT_ID,
            "Schreibtisch": SCHREIBTISCH_ID,
        }
    
    res_Bett = proxy_hmip.getValue(light_id_dic["Bett"], "STATE")
    res_Schreibtisch = proxy_hmip.getValue(light_id_dic["Schreibtisch"], "STATE")
    print("Licht Bett ist auf " + str(res_Bett) + " gesetzt")
    print("Licht Schreibtisch ist auf " + str(res_Schreibtisch) + " gesetzt")

    return [res_Schreibtisch, res_Bett]

SHUTTER_ID = os.getenv("SHUTTER_ID")

def update_real_shutter(level):
    global proxy_hm
    id = SHUTTER_ID

    if level == 1.0:
        updated_status = False
    if level == 0.0:
        updated_status = True

    try:
        proxy_hm.setValue(id, "LEVEL", level)
        print("Rollo " + str(id) + " wird auf " + str(level) + " gesetzt")
        return updated_status
    except xmlrpc.client.Fault as fault:
        print("Fehler: " + str(fault))
        return not updated_status
    except Exception as err:
        print("Fehler: " + str(err))
        return not updated_status

def get_real_shutter():
    global proxy_hm
    id = SHUTTER_ID

    try:
        level = proxy_hm.getValue(id, "LEVEL")
        print("Rollo " + str(id) + " ist auf " + str(level) + " gesetzt")
        if level == 0.0:
            return True
        else:
            return False
    except xmlrpc.client.Fault as fault:
        print("Fehler: " + str(fault))
        return False
    except Exception as err:
        print("Fehler: " + str(err))
        return False

def change_debug_mode(e):
    global debug
    if debug == True:
        debug = False
    else:
        debug = True

window = tk.Tk()
window.title("Smart Home Steuerung")
window.attributes("-fullscreen", True)
window.bind_all("<Escape>", exit_program)
window.bind_all("d", change_debug_mode)
window.config(cursor="none")
window.after(100, evaluate_camera)

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

canvas = tk.Canvas(
    window, 
    width=screen_width, 
    height=screen_height, 
    bg="white", 
    bd=0, 
    highlightthickness=0
)
canvas.pack(fill="both", expand=True)

prefix_hidden = "images/shutter_hidden/renders/"
prefix_shown = "images/shutter_shown/renders/"
bg_images = {
    (False, False, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "base.png").resize((screen_width, screen_height))),
    (True, False, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
    (False, True, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "light.Lampe_Bett.png").resize((screen_width, screen_height))),
    (True, True, False): ImageTk.PhotoImage(Image.open(prefix_hidden + "light.Lampe_Bett_light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
    
    (False, False, True): ImageTk.PhotoImage(Image.open(prefix_shown + "base.png").resize((screen_width, screen_height))),
    (True, False, True): ImageTk.PhotoImage(Image.open(prefix_shown + "light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
    (False, True, True): ImageTk.PhotoImage(Image.open(prefix_shown + "light.Lampe_Bett.png").resize((screen_width, screen_height))),
    (True, True, True): ImageTk.PhotoImage(Image.open(prefix_shown + "light.Lampe_Bett_light.Lampe_Schreibtisch.png").resize((screen_width, screen_height))),
}

bg_id = canvas.create_image(0, 0, image=bg_images[(False, False, False)], anchor="nw")
lights = get_real_light()
shutter = get_real_shutter()
update_bg()

window.mainloop()




