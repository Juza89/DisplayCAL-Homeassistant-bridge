DisplayCAL to Home Assistant Bridge (Light Calibration Tool)

A Python-based GUI application that acts as a bridge between DisplayCAL and Home Assistant. This tool allows you to use professional colorimetry software (ArgyllCMS/DisplayCAL) and a hardware colorimeter to profile and calibrate physical RGB smart room lights, essentially treating your room like a 1-pixel monitor.

Features:

    GUI: A clean, easy-to-use interface built using customtkinter.  

    Auto-Discovery: Automatically fetches and lists all available light. entities from your Home Assistant instance. (Search included!)

    Live Color Conversion: Seamlessly polls the DisplayCAL web server for hex color values and translates them into hs_color (Hue/Saturation) and brightness payloads for Home Assistant.  

    Real-time Preview: Includes a visual color box in the UI that displays the current color being sent to the light.  

    Persistent Settings: Automatically saves your HA URL, token, and selected light to a local config.json file so you don't have to re-enter them every time.
