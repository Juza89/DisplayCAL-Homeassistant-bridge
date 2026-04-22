import customtkinter as ctk
import threading
import requests
import time
import traceback
import colorsys
import json
import os

# Set the visual theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

class CalibrationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DisplayCAL ➔ Home Assistant Bridge")
        self.geometry("550x650")
        self.is_running = False

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)

        # 1. Configuration Frame
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.config_frame, text="Entity ID:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entity_entry = ctk.CTkEntry(self.config_frame)
        self.entity_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.config_frame, text="HA Base URL:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(self.config_frame)
        self.url_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.config_frame, text="HA Token:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.token_entry = ctk.CTkEntry(self.config_frame)
        self.token_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.config_frame, text="DisplayCAL:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.dc_url_entry = ctk.CTkEntry(self.config_frame)
        self.dc_url_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # 2. Controls Frame
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.control_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.status_label = ctk.CTkLabel(self.control_frame, text="Status: STOPPED", text_color="gray", font=("Arial", 14, "bold"))
        self.status_label.grid(row=0, column=0, padx=10, pady=15, sticky="w")

        self.start_button = ctk.CTkButton(self.control_frame, text="Start Sync", command=self.toggle_sync, fg_color="green", hover_color="darkgreen")
        self.start_button.grid(row=0, column=1, padx=10, pady=15)

        self.color_box_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.color_box_frame.grid(row=0, column=2, padx=10, pady=15, sticky="e")
        ctk.CTkLabel(self.color_box_frame, text="Current:").pack(side="left", padx=(0, 10))
        self.color_box = ctk.CTkFrame(self.color_box_frame, width=40, height=40, fg_color="#404040", corner_radius=6)
        self.color_box.pack(side="left")

        # 3. Log Output
        ctk.CTkLabel(self, text="Application Log:").grid(row=2, column=0, padx=20, sticky="w")
        self.log_box = ctk.CTkTextbox(self, height=200, state="disabled")
        self.log_box.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.grid_rowconfigure(3, weight=1)

        self.load_settings()
        self.log("Application started. Ready to sync.")

    # --- SETTINGS MANAGEMENT ---
    def save_settings(self):
        data = {
            "entity": self.entity_entry.get(),
            "ha_url": self.url_entry.get(),
            "token": self.token_entry.get(),
            "dc_url": self.dc_url_entry.get()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.entity_entry.insert(0, data.get("entity", "light.ceiling_light"))
                    self.url_entry.insert(0, data.get("ha_url", "http://homeassistant:8123"))
                    self.token_entry.insert(0, data.get("token", "INSERT YOUR LONG TOKEN HERE"))
                    self.dc_url_entry.insert(0, data.get("dc_url", "http://127.0.0.1:8080/ajax/messages"))
            except:
                pass
        else:
            self.entity_entry.insert(0, "light.ceiling_light")
            self.url_entry.insert(0, "http://homeassistant:8123")
            self.dc_url_entry.insert(0, "http://127.0.0.1:8080/ajax/messages")

    # --- HELPER METHODS ---
    def log(self, message):
        def update():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, update)

    def update_color_box(self, hex_color):
        def update():
            self.color_box.configure(fg_color=hex_color)
        self.after(0, update)

    @staticmethod
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

    @staticmethod
    def rgb_to_hex(rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def rgb_to_hs_payload(self, rgb, entity_id):
        r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        brightness = int(round(v * 255))
        if brightness <= 0:
            return {"entity_id": entity_id, "brightness": 0, "effect": "none"}
        if s < 0.001: s = 0.001
        return {
            "entity_id": entity_id,
            "hs_color": [round(h * 360, 3), round(s * 100, 3)],
            "brightness": max(1, brightness),
            "effect": "none"
        }

    def toggle_sync(self):
        if not self.is_running:
            self.save_settings()
            self.is_running = True
            self.status_label.configure(text="Status: RUNNING", text_color="green")
            self.start_button.configure(text="Stop Sync", fg_color="red", hover_color="darkred")
            self.log("Starting Bridge...")
            threading.Thread(target=self.run_bridge, daemon=True).start()
        else:
            self.is_running = False
            self.status_label.configure(text="Status: STOPPING...", text_color="orange")

    def run_bridge(self):
        ha_url_base = self.url_entry.get().rstrip('/')
        ha_url_full = f"{ha_url_base}/api/services/light/turn_on"
        ha_token = self.token_entry.get()
        entity_id = self.entity_entry.get()
        dc_url = self.dc_url_entry.get()

        headers_ha = {"Authorization": f"Bearer {ha_token}", "content-type": "application/json"}

        current_bg = "#000000"
        last_dc_error = None
        last_ha_error = None
        POLL_INTERVAL = 0.1 

        while self.is_running:
            loop_start = time.time()

            try:
                # 1. Fetch from DisplayCAL
                try:
                    response_dc = requests.get(f"{dc_url}?{current_bg} {time.time()}", timeout=5)
                    response_dc.raise_for_status()
                    new_hex = response_dc.text.strip()
                    
                    if last_dc_error:
                        self.log("DisplayCAL connection recovered!")
                        last_dc_error = None

                except Exception as e:
                    error_msg = f"DisplayCAL Error: {str(e)}"
                    if error_msg != last_dc_error:
                        self.log(error_msg)
                        last_dc_error = error_msg
                    new_hex = None # Ensure we don't process a failed request

                # 2. Only Process if we have a NEW color
                if new_hex and new_hex != current_bg:
                    rgb = self.hex_to_rgb(new_hex)
                    payload = self.rgb_to_hs_payload(rgb, entity_id)
                    max_channel = max(rgb)

                    # Proportional Scaling for UI Visuals
                    if max_channel < 40:
                        if max_channel == 0:
                            visual_rgb = [0, 0, 0]
                        else:
                            scale_factor = 40 / max_channel
                            visual_rgb = [int(c * scale_factor) for c in rgb]
                    else:
                        visual_rgb = rgb
                    
                    self.update_color_box(self.rgb_to_hex(visual_rgb))

                    # 3. Post to Home Assistant
                    try:
                        res_ha = requests.post(ha_url_full, json=payload, headers=headers_ha, timeout=2)
                        
                        if res_ha.status_code == 401:
                            self.log("HA Error: 401 Unauthorized. Check your Token!")
                            self.is_running = False
                            break
                        elif res_ha.status_code == 404:
                            self.log("HA Error: 404 Not Found. Check your Base URL!")
                            self.is_running = False
                            break
                        
                        res_ha.raise_for_status()
                        self.log(f"In RGB: {rgb} -> HS: {payload.get('hs_color')} | V: {payload.get('brightness')}")
                        
                        current_bg = new_hex
                        
                        if last_ha_error:
                            self.log("HA connection recovered!")
                            last_ha_error = None

                    except Exception as e:
                        error_msg = f"HA Post Error: {str(e)}"
                        if error_msg != last_ha_error:
                            self.log(error_msg)
                            last_ha_error = error_msg

            except Exception as e:
                self.log(f"General Loop Error: {e}")

            # Enforce the 100ms polling rate
            elapsed = time.time() - loop_start
            time.sleep(max(0.01, POLL_INTERVAL - elapsed))

        self.cleanup_ui()

    def cleanup_ui(self):
        def reset():
            self.status_label.configure(text="Status: STOPPED", text_color="gray")
            self.start_button.configure(text="Start Sync", fg_color="green", hover_color="darkgreen", state="normal")
            self.update_color_box("#404040")
            self.log("Bridge stopped.")
        self.after(0, reset)

if __name__ == "__main__":
    app = CalibrationApp()
    app.mainloop()
