"""
Fixed tasks.py - Resolves async context errors and improves detection
"""
import os
import cv2
try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
import time
import asyncio
from threading import Thread
from asgiref.sync import sync_to_async, async_to_sync
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from .models import Alert, DriverProfile
from .detection_factory import get_detector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def drowsiness_detection_task_sync(
    webcam_index, ear_thresh, ear_frames, yawn_thresh, driver_profile, driver_email
):
    """
    SYNCHRONOUS drowsiness detection task - FIXED VERSION
    This runs in a separate thread to avoid async context issues
    """
    print("✅ Drowsiness detection task started (SYNC VERSION).")
    
    # Initialize pygame for audio alerts
    try:
        if PYGAME_AVAILABLE:
            pygame.mixer.init()
            audio_path = os.path.join(BASE_DIR, "static", "music.wav")
            if os.path.exists(audio_path):
                pygame.mixer.music.load(audio_path)
                print("✅ Audio system initialized")
            else:
                print("⚠️ Audio file not found, alerts will be silent")
        else:
            print("⚠️ Pygame not available - audio alerts disabled")
    except Exception as e:
        print(f"⚠️ Audio initialization failed: {e}")

    print("-> Loading detection system...")
    try:
        detector = get_detector()
        if detector is None:
            print("❌ Error: No detection system available!")
            return
        print(f"✅ Using detector: {type(detector).__name__}")
    except Exception as e:
        print(f"❌ Error loading detector: {e}")
        return

    print("-> Starting Video Stream")
    try:
        cap = cv2.VideoCapture(webcam_index)
        if not cap.isOpened():
            raise Exception(f"Cannot open camera {webcam_index}")
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("✅ Video stream opened successfully.")
    except Exception as e:
        print(f"❌ Error opening video stream: {e}")
        return

    # Detection state variables
    drowsy_counter = 0
    yawn_counter = 0
    last_alert_time = 0
    alert_cooldown = 5  # seconds

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ No video frame received.")
                break

            # Resize frame for better performance
            frame = cv2.resize(frame, (640, 480))

            try:
                # Use the detection system
                is_drowsy, is_yawning, annotated_frame = detector.detect_drowsiness(frame)

                current_time = time.time()
                alert_triggered = False

                # Handle drowsiness detection
                if is_drowsy:
                    drowsy_counter += 1
                    if drowsy_counter >= ear_frames:
                        if current_time - last_alert_time > alert_cooldown:
                            alert_triggered = True
                            create_alert_sync(
                                driver_profile, 
                                "drowsiness", 
                                "Drowsiness detected!",
                                driver_email
                            )
                            play_alert_sync("Drowsiness Alert!")
                            last_alert_time = current_time
                            print("🚨 Drowsiness alert triggered!")
                        drowsy_counter = 0  # Reset after alert
                else:
                    drowsy_counter = 0

                # Handle yawn detection
                if is_yawning:
                    yawn_counter += 1
                    if yawn_counter >= 3:  # Lower threshold for yawning
                        if current_time - last_alert_time > alert_cooldown:
                            alert_triggered = True
                            create_alert_sync(
                                driver_profile,
                                "yawning", 
                                "Excessive yawning detected!",
                                driver_email
                            )
                            play_alert_sync("Yawn Alert!")
                            last_alert_time = current_time
                            print("🚨 Yawn alert triggered!")
                        yawn_counter = 0  # Reset after alert
                else:
                    yawn_counter = 0

                # Display the annotated frame
                cv2.imshow("DrowsiSense - Driver Monitoring", annotated_frame)

                # Check for quit key
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("👋 User requested quit")
                    break

                # Control frame rate (~30 FPS)
                time.sleep(0.033)

            except Exception as e:
                print(f"⚠️ Error in detection loop: {e}")
                # Continue with basic frame display
                cv2.imshow("DrowsiSense - Driver Monitoring", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

    except KeyboardInterrupt:
        print("👋 Detection stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Drowsiness detection task completed.")


def create_alert_sync(driver_profile, alert_type, description, driver_email):
    """Create alert synchronously to avoid async context issues"""
    try:
        # Create alert in database
        alert = Alert.objects.create(
            driver=driver_profile,
            alert_type=alert_type,
            description=description,
            severity='high' if alert_type == 'drowsiness' else 'medium',
            confidence=0.9
        )
        print(f"✅ Alert created: {alert_type}")
        
        # Send real-time update to dashboard
        try:
            from ..utils.realtime_updates import send_alert_to_user
            alert_data = {
                'id': alert.id,
                'alert_type': alert.alert_type,
                'description': alert.description,
                'severity': alert.severity,
                'timestamp': alert.timestamp.isoformat(),
                'status': alert.status
            }
            send_alert_to_user(driver_profile.user.id, alert_data)
        except Exception as e:
            print(f"⚠️ Real-time update failed: {e}")
        
        # Send email alert in background thread to avoid blocking
        def send_email_background():
            try:
                send_email_alert_sync(alert, driver_profile, driver_email)
            except Exception as e:
                print(f"⚠️ Email sending failed: {e}")
        
        Thread(target=send_email_background, daemon=True).start()
        
    except Exception as e:
        print(f"❌ Failed to create alert: {e}")


def send_email_alert_sync(alert, driver_profile, driver_email):
    """Send email alert synchronously"""
    try:
        if alert.alert_type == "drowsiness":
            subject = "🚨 Drowsiness Alert - Immediate Attention Required"
        else:
            subject = "⚠️ Fatigue Alert - Driver Monitoring System"
            
        context = {
            "driver": driver_profile,
            "alert": alert,
            "driver_first_name": driver_profile.user.first_name or "Driver",
        }
        
        message = render_to_string("drowsiness_alert.html", context)
        email = EmailMessage(subject, message, to=[driver_email])
        email.content_subtype = "html"
        
        email.send()
        print(f"📧 Email alert sent to {driver_email}")
        
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")


def play_alert_sync(message):
    """Play audio alert synchronously"""
    try:
        # Play audio file
        if PYGAME_AVAILABLE:
            pygame.mixer.music.play()
            print("🔊 Audio alert played")
        else:
            print("⚠️ Audio alert skipped - pygame not available")
    except Exception as e:
        print(f"⚠️ Audio playback failed: {e}")
    
    try:
        # Windows TTS using pyttsx3 (better than espeak on Windows)
        if os.name == 'nt':  # Windows
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 200)  # Speed
                engine.setProperty('volume', 0.9)  # Volume
                engine.say(message)
                engine.runAndWait()
                print("🗣️ TTS alert played")
            except ImportError:
                print("⚠️ pyttsx3 not available, skipping TTS")
            except Exception as e:
                print(f"⚠️ TTS failed: {e}")
        else:
            # Linux/Mac - use espeak if available
            try:
                os.system(f'espeak "{message}"')
            except Exception as e:
                print(f"⚠️ espeak failed: {e}")
                
    except Exception as e:
        print(f"⚠️ TTS system failed: {e}")


# Keep the async version for compatibility but redirect to sync version
async def drowsiness_detection_task(*args, **kwargs):
    """
    Async wrapper that calls the sync version in a thread
    """
    print("🔄 Redirecting to sync detection task...")
    
    # Run the sync version in a separate thread
    def run_sync():
        drowsiness_detection_task_sync(*args, **kwargs)
    
    thread = Thread(target=run_sync, daemon=True)
    thread.start()
    
    # Return immediately - the detection runs in background
    print("✅ Detection task started in background thread")