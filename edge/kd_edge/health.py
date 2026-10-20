import cv2

def check_camera_health(frame, s):
    """OK, OFFLINE, BLOCKED, TOO_DARK or BLURRED. A bad camera must never look like an empty room."""
    if frame is None:
        return "OFFLINE"
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if gray.std() < s.min_contrast:
        return "BLOCKED"
    if gray.mean() < s.min_brightness:
        return "TOO_DARK"
    if cv2.Laplacian(gray, cv2.CV_64F).var() < s.min_sharpness:
        return "BLURRED"
    return "OK"
