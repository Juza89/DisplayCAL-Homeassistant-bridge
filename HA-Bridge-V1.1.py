import customtkinter as ctk
import threading
import requests
import time
import colorsys
import json
import os

CONFIG_FILE = "config.json"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# ---------------- APP ----------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Light Calibration Tool")
        self.geometry("600x650")

        # Removed /ajax/messages from the default so it doesn't show in the UI
        self.config_data = {
            "url": "http://homeassistant:8123", 
            "token": "PASTE LONG_LIVED ACCESS TOKEN", 
            "dc_url": "http://127.0.0.1:8080", 
            "entity": "", 
            "lights": []
        }
        self.current_frame = None
        self.is_running = False

        self.load_config()

        # Route the user based on saved data
        if self.config_data.get("entity") and self.config_data.get("token"):
            self.show_frame(CalibrationFrame)
        else:
            self.show_frame(SetupFrame)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config_data.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config_data, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def show_frame(self, frame_class):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame_class(self)
        self.current_frame.pack(fill="both", expand=True)


# ---------------- SETUP ----------------
class SetupFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(self, text="Connect to Home Assistant", font=("Arial", 18, "bold")).pack(pady=20)

        # HA URL
        ctk.CTkLabel(self, text="Home Assistant Base URL:").pack(anchor="w", padx=40)
        self.url = ctk.CTkEntry(self, placeholder_text="http://homeassistant:8123")
        self.url.pack(fill="x", padx=40, pady=(0, 10))
        self.url.insert(0, master.config_data.get("url") or "http://homeassistant:8123")

        # HA Token
        ctk.CTkLabel(self, text="Long-Lived Access Token:").pack(anchor="w", padx=40)
        self.token = ctk.CTkEntry(self, placeholder_text="Paste LONG-LIVED Access Token", show="*")
        self.token.pack(fill="x", padx=40, pady=(0, 10))
        self.token.insert(0, master.config_data.get("token") or "")

        # DisplayCAL URL (Cleaned up)
        ctk.CTkLabel(self, text="DisplayCAL Web Server URL:").pack(anchor="w", padx=40)
        self.dc_url = ctk.CTkEntry(self, placeholder_text="http://127.0.0.1:8080")
        self.dc_url.pack(fill="x", padx=40, pady=(0, 10))
        self.dc_url.insert(0, master.config_data.get("dc_url") or "http://127.0.0.1:8080")

        self.status = ctk.CTkLabel(self, text="")
        self.status.pack(pady=5)

        ctk.CTkButton(self, text="Next", command=self.connect).pack(pady=10)
        
        # Optional back button if they came from Calibration Frame
        if master.config_data.get("entity"):
            ctk.CTkButton(self, text="Cancel", fg_color="gray", command=lambda: master.show_frame(CalibrationFrame)).pack(pady=5)

    def connect(self):
        self.status.configure(text="Connecting...")

        def worker():
            try:
                # Sanitize the token to prevent accidental spaces/quotes
                raw_token = self.token.get().strip()
                clean_token = raw_token.replace('"', '').replace("'", "")
                
                url = self.url.get().rstrip("/") + "/api/states"
                res = requests.get(url, headers={"Authorization": f"Bearer {clean_token}"}, timeout=5)
                res.raise_for_status()
                data = res.json()

                # Fetch lights
                lights = sorted([e["entity_id"] for e in data if e["entity_id"].startswith("light.")])

                # Update global config (strip any stray trailing slashes from the DC URL)
                self.master.config_data.update({
                    "url": self.url.get().rstrip("/"),
                    "token": clean_token,
                    "dc_url": self.dc_url.get().strip().rstrip("/"),
                    "lights": lights
                })
                self.master.save_config()

                self.after(0, lambda: self.master.show_frame(SelectLightFrame))

            except Exception as e:
                self.after(0, lambda: self.status.configure(text=f"❌ Connection Failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()


# ---------------- SELECT LIGHT ----------------
class SelectLightFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(self, text="Select Light", font=("Arial", 18, "bold")).pack(pady=20)

        self.search = ctk.CTkEntry(self, placeholder_text="Search...")
        self.search.pack(fill="x", padx=40, pady=5)
        self.search.bind("<KeyRelease>", self.update_list)

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=40, pady=10)

        self.selected = master.config_data.get("entity", None)
        self.buttons = []

        self.update_list()

        ctk.CTkButton(self, text="Next", command=self.next).pack(pady=(10, 5))
        ctk.CTkButton(self, text="Back to Setup", fg_color="gray", command=lambda: master.show_frame(SetupFrame)).pack(pady=(0, 10))

    def update_list(self, event=None):
        for b in self.buttons:
            b.destroy()
        self.buttons = []

        term = self.search.get().lower()
        for e in self.master.config_data.get("lights", []):
            if term in e:
                btn = ctk.CTkButton(self.scroll, text=e, anchor="w", fg_color="transparent", text_color=("gray10", "gray90"))
                btn.configure(command=lambda x=e, b=btn: self.select(x, b))
                btn.pack(fill="x", pady=2)
                
                # Pre-highlight if it's the currently saved entity
                if e == self.selected:
                    btn.configure(fg_color=("gray75", "gray25"))
                    
                self.buttons.append(btn)

    def select(self, e, clicked_btn):
        self.selected = e
        for b in self.buttons:
            b.configure(fg_color="transparent")
        clicked_btn.configure(fg_color=("green", "darkgreen"))

    def next(self):
        if not self.selected:
            return
        self.master.config_data["entity"] = self.selected
        self.master.save_config()
        self.master.show_frame(CalibrationFrame)


# ---------------- CALIBRATION ----------------
class CalibrationFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        ctk.CTkLabel(self, text="Calibration Active", font=("Arial", 18, "bold")).pack(pady=10)

        target = master.config_data.get("entity", "Unknown Light")
        ctk.CTkLabel(self, text=f"Target: {target}", text_color="gray").pack()

        self.status = ctk.CTkLabel(self, text="Status: STOPPED", text_color="gray", font=("Arial", 14, "bold"))
        self.status.pack(pady=5)

        self.color_box = ctk.CTkFrame(self, width=80, height=80, fg_color="#404040", corner_radius=6)
        self.color_box.pack(pady=10)

        self.start_btn = ctk.CTkButton(self, text="Start Calibration", command=self.toggle, fg_color="green", hover_color="darkgreen")
        self.start_btn.pack(pady=10)

        ctk.CTkButton(self, text="Change Settings", fg_color="gray", command=self.go_back).pack(pady=5)

        self.log = ctk.CTkTextbox(self, height=200)
        self.log.pack(fill="both", expand=True, padx=20, pady=10)

    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def go_back(self):
        self.master.is_running = False
        self.master.show_frame(SetupFrame)

    def toggle(self):
        if not self.master.is_running:
            self.master.is_running = True
            self.start_btn.configure(text="Stop Sync", fg_color="red", hover_color="darkred")
            self.status.configure(text="Status: RUNNING", text_color="green")
            self.log_msg("Starting Bridge...")
            threading.Thread(target=self.loop, daemon=True).start()
        else:
            self.master.is_running = False
            self.start_btn.configure(text="Start Calibration", fg_color="green", hover_color="darkgreen")
            self.status.configure(text="Status: STOPPED", text_color="gray")
            self.color_box.configure(fg_color="#404040")

    def loop(self):
        cfg = self.master.config_data
        current_bg = "#000000"
        
        headers_ha = {"Authorization": f"Bearer {cfg['token']}", "content-type": "application/json"}
        ha_url_full = cfg["url"].rstrip("/") + "/api/services/light/turn_on"
        
        # Build the full DisplayCAL API path here, completely hidden from the user
        dc_url_base = cfg.get("dc_url", "http://127.0.0.1:8080").rstrip("/")
        dc_url_full = f"{dc_url_base}/ajax/messages"

        last_dc_error = None
        last_ha_error = None
        POLL_INTERVAL = 0.1

        while self.master.is_running:
            loop_start = time.time()
            new_hex = None

            try:
                # 1. Fetch from DisplayCAL (Fix: Using dc_url_full now)
                try:
                    response_dc = requests.get(f"{dc_url_full}?{current_bg} {time.time()}", timeout=5)
                    response_dc.raise_for_status()
                    new_hex = response_dc.text.strip()
                    
                    if last_dc_error:
                        self.log_msg("DisplayCAL connection recovered!")
                        last_dc_error = None

                except Exception as e:
                    error_msg = f"DisplayCAL Error: {str(e)}"
                    if error_msg != last_dc_error:
                        self.log_msg(error_msg)
                        last_dc_error = error_msg
                    new_hex = None # Ensure we don't process a failed request

                # 2. Process & Post only IF New color!
                if new_hex and new_hex != current_bg:
                    rgb = [int(new_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
                    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    brightness = int(round(v * 255))
                    
                    if brightness <= 0:
                        payload = {"entity_id": cfg["entity"], "brightness": 0, "effect": "none"}
                    else:
                        if s < 0.001: s = 0.001 
                        payload = {
                            "entity_id": cfg["entity"],
                            "hs_color": [round(h * 360, 3), round(s * 100, 3)],
                            "brightness": max(1, brightness),
                            "effect": "none"
                        }
                    
                    # UI visual scaling
                    max_channel = max(rgb)
                    if max_channel < 40:
                        if max_channel == 0:
                            visual_rgb = [0, 0, 0]
                        else:
                            scale_factor = 40 / max_channel
                            visual_rgb = [int(c * scale_factor) for c in rgb]
                    else:
                        visual_rgb = rgb

                    visual_hex = f"#{visual_rgb[0]:02x}{visual_rgb[1]:02x}{visual_rgb[2]:02x}"
                    self.after(0, lambda c=visual_hex: self.color_box.configure(fg_color=c))

                    # 3. Post to Home Assistant
                    try:
                        res_ha = requests.post(ha_url_full, json=payload, headers=headers_ha, timeout=2)
                        
                        if res_ha.status_code == 401:
                            self.log_msg("HA Error: 401 Unauthorized. Check your Token!")
                            self.master.is_running = False
                            break
                        elif res_ha.status_code == 404:
                            self.log_msg("HA Error: 404 Not Found. Check your Base URL!")
                            self.master.is_running = False
                            break
                        
                        res_ha.raise_for_status()
                        self.log_msg(f"In RGB: {rgb} -> HS: {payload.get('hs_color')} | V: {payload.get('brightness')}")
                        
                        current_bg = new_hex
                        
                        if last_ha_error:
                            self.log_msg("HA connection recovered!")
                            last_ha_error = None

                    except Exception as e:
                        error_msg = f"HA Post Error: {str(e)}"
                        if error_msg != last_ha_error:
                            self.log_msg(error_msg)
                            last_ha_error = error_msg

            except Exception as e:
                self.log_msg(f"General Loop Error: {e}")

            elapsed = time.time() - loop_start
            time.sleep(max(0.01, POLL_INTERVAL - elapsed))

        self.after(0, self.cleanup_ui)

    def cleanup_ui(self):
        self.status.configure(text="Status: STOPPED", text_color="gray")
        self.start_btn.configure(text="Start Calibration", fg_color="green", hover_color="darkgreen", state="normal")
        self.color_box.configure(fg_color="#404040")
        self.log_msg("Bridge stopped.")

if __name__ == "__main__":
    App().mainloop()