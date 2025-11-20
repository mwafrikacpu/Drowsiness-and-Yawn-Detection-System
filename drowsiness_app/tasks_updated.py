"""
Updated tasks.py that works with multiple detection backends
Compatible with Windows installations that may not have dlib
"""
import asyncio
import os
import cv2
try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
import numpy as np
from asgiref.sync import sync_to_async
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from .models import Alert, DriverProfile
from .detection_factory import get_detector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def drowsiness_detection_task(
    webcam_index, ear_thresh, ear_frames, yawn_thresh, driver_profile, driver_email
):
    """
    Updated drowsiness detection task with fallback detection methods
    """
    print("Drowsiness detection task started.")
    alarm_status = False
    alarm_status2 = False
    saying = False
    drowsiness_detected = False

    # Initialize pygame for audio alerts
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(os.path.join(BASE_DIR, "static/music.wav"))
    except Exception as e:
        print(f"Warning: Could not load audio file: {e}")

    print("-> Loading detection system...")
    try:
        detector = get_detector()
        if detector is None:
            print("Error: No detection system available!")
            return
        print(f"-> Using detector: {type(detector).__name__}")
    except Exception as e:
        print(f"Error loading detector: {e}")
        return

    print("-> Starting Video Stream")
    try:
        vs = cv2.VideoCapture(webcam_index)
        if not vs.isOpened():
            raise Exception(f"Cannot open camera {webcam_index}")
        print("Video stream opened successfully.")
    except Exception as e:
        print(f"Error opening video stream: {e}")
        return

    await asyncio.sleep(1.0)  # Allow the video stream to warm up

    COUNTER = 0
    yawn_counter = 0

    try:
        while True:
            ret, frame = vs.read()
            if not ret or frame is None:
                print("Error: No video frame received.")
                break

            # Resize frame for better performance
            frame = cv2.resize(frame, (640, 480))

            try:
                # Use the detection system
                is_drowsy, is_yawning, annotated_frame = detector.detect_drowsiness(frame)

                # Handle drowsiness detection
                if is_drowsy:
                    COUNTER += 1
                    if COUNTER >= ear_frames:
                        if not drowsiness_detected:
                            drowsiness_detected = True
                            msg = "Drowsiness detected!"
                            print("Drowsiness alert triggered!")
                            
                            # Play audio alert
                            try:
                                pygame.mixer.music.play()
                            except:
                                print("Could not play audio alert")

                            # Text-to-speech (optional, may not work on all systems)
                            try:
                                if os.name == 'nt':  # Windows
                                    import pyttsx3
                                    engine = pyttsx3.init()
                                    engine.say(msg)
                                    engine.runAndWait()
                                else:  # Linux/Mac
                                    s = 'espeak "' + msg + '"'
                                    await sync_to_async(os.system)(s)
                            except:
                                print("Text-to-speech not available")

                            # Save alert to database
                            alert = Alert(
                                driver=driver_profile,
                                alert_type="drowsiness",
                                description=msg,
                            )
                            await sync_to_async(alert.save, thread_sensitive=True)()

                            # Send email alert
                            try:
                                await send_email_alert(alert, driver_profile, driver_email)
                            except Exception as e:
                                print(f"Could not send email: {e}")
                else:
                    COUNTER = 0
                    drowsiness_detected = False

                # Handle yawn detection
                if is_yawning:
                    yawn_counter += 1
                    if yawn_counter >= 2:  # Reduced threshold for yawning
                        msg = "Yawn Alert"
                        if not alarm_status2 and not saying:
                            alarm_status2 = True
                            print("Yawn alert triggered!")
                            
                            # Play audio alert
                            try:
                                pygame.mixer.music.play()
                            except:
                                print("Could not play audio alert")

                            # Text-to-speech
                            try:
                                saying = True
                                if os.name == 'nt':  # Windows
                                    import pyttsx3
                                    engine = pyttsx3.init()
                                    engine.say(msg)
                                    engine.runAndWait()
                                else:
                                    s = 'espeak "' + msg + '"'
                                    await sync_to_async(os.system)(s)
                                saying = False
                            except:
                                saying = False
                                print("Text-to-speech not available")

                            # Save alert to database
                            alert = Alert(
                                driver=driver_profile, 
                                alert_type="yawning", 
                                description=msg
                            )
                            await sync_to_async(alert.save, thread_sensitive=True)()

                            alarm_status2 = False
                            yawn_counter = 0
                else:
                    yawn_counter = 0
                    alarm_status2 = False

                # Display the annotated frame
                cv2.imshow("DrowsiSense - Driver Monitoring", annotated_frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

            except Exception as e:
                print(f"Error in detection loop: {e}")
                # Continue with basic frame display
                cv2.imshow("DrowsiSense - Driver Monitoring", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

            await asyncio.sleep(0.033)  # ~30 FPS

    except KeyboardInterrupt:
        print("Detection stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cv2.destroyAllWindows()
        vs.release()
        print("Drowsiness detection task completed.")


async def send_email_alert(alert, driver_profile, driver_email):
    """Send email alert for drowsiness/yawn detection"""
    try:
        if alert.alert_type == "drowsiness":
            subject = "Drowsiness Alert - Immediate Attention Required"
            email_template = "drowsiness_alert.html"
        else:
            subject = "Fatigue Alert - Driver Monitoring System"
            email_template = "drowsiness_alert.html"  # Use same template
            
        context = {
            "driver": driver_profile,
            "alert": alert,
            "driver_first_name": driver_profile.user.first_name,
        }
        
        message = render_to_string(email_template, context)
        email = EmailMessage(subject, message, to=[driver_email])
        email.content_subtype = "html"
        
        await sync_to_async(email.send)()
        print(f"Email alert sent to {driver_email}")
        
    except Exception as e:
        print(f"Failed to send email alert: {e}")


# Backwards compatibility function
async def drowsiness_detection_task_legacy(*args, **kwargs):
    """Legacy function name for backwards compatibility"""
    return await drowsiness_detection_task(*args, **kwargs)