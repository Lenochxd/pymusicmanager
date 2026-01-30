def placeholders(track: str, string: str, extension: str = "") -> str:
    string_bcp = string
    
    string = string.replace("{title}", track.get("title", "Unknown Track").replace("/", "_"))
    string = string.replace("{album}", track.get("album", "Unknown Album").replace("/", "_"))
    string = string.replace("{artist}", track.get("artists", ["Unknown Artist"])[0].replace("/", "_"))
    string = string.replace("{track}", str(track.get("track_number", "")))
    string = string.replace("{track_number}", str(track.get("track_number", "")))
    string = string.replace("{disc}", str(track.get("disc_number", "")))
    string = string.replace("{disc_number}", str(track.get("disc_number", "")))
    string = string.replace("{duration_ms}", str(track.get("duration_ms", "")))
    string = string.replace("{duration}", str(track.get("duration", "")))
    string = string.replace("{provider_id}", track.get("provider_id", ""))
    string = string.replace("{source}", track.get("source", ""))
    string = string.replace("{platform}", track.get("source", ""))
    string = string.replace("{uri}", track.get("uri", ""))
    string = string.replace("{provider_id}", track.get("provider_id", ""))
    
    print(f"Placeholders: '{string_bcp}' -> '{string}'")
    return string + extension
