"""
Detection Engine - Improved task execution with better architecture
"""
import asyncio
import logging
from typing import Dict, Any, Optional
import cv2
try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
import os
from asgiref.sync import sync_to_async

from ..detection_factory import get_detector
from ..services.alert_service import alert_service
from ..core.exceptions import DetectionError, CameraError, AudioError
from ..models import DriverProfile


logger = logging.getLogger(__name__)


class DetectionEngine:
    """
    Main detection engine that orchestrates the monitoring process
    """
    
    def __init__(self):
        self.detector = None
        self.is_running = False
        self.camera = None
        self.audio_initialized = False
        
        # Detection state
        self.consecutive_drowsy_frames = 0
        self.consecutive_yawn_frames = 0
        self.last_drowsy_alert_time = 0
        self.last_yawn_alert_time = 0
        
        # Configuration
        self.config = {}
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the detection engine
        Args:
            config: Configuration dictionary
        Returns: True if initialization successful
        """
        try:
            self.config = config
            
            # Initialize detector
            self.detector = get_detector()
            if not self.detector:
                raise DetectionError("Failed to initialize detector")
            
            # Initialize camera
            await self._initialize_camera(config.get('camera_index', 0))
            
            # Initialize audio
            await self._initialize_audio()
            
            logger.info("Detection engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize detection engine: {e}")
            raise DetectionError(f"Initialization failed: {e}")
    
    async def start_monitoring(
        self,
        driver_profile: DriverProfile,
        settings: Dict[str, Any]
    ) -> None:
        """
        Start the monitoring process
        Args:
            driver_profile: Driver profile instance
            settings: Detection settings
        """
        if self.is_running:
            logger.warning("Monitoring already in progress")
            return
        
        try:
            self.is_running = True
            await self._monitoring_loop(driver_profile, settings)
            
        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            raise DetectionError(f"Monitoring failed: {e}")
        finally:
            await self.stop_monitoring()
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring process"""
        try:
            self.is_running = False
            
            if self.camera:
                self.camera.release()
                self.camera = None
            
            cv2.destroyAllWindows()
            logger.info("Monitoring stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
    
    async def _initialize_camera(self, camera_index: int) -> None:
        """Initialize camera"""
        try:
            self.camera = cv2.VideoCapture(camera_index)
            if not self.camera.isOpened():
                raise CameraError(f"Cannot open camera {camera_index}")
            
            # Set camera properties for better performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            logger.info(f"Camera {camera_index} initialized successfully")
            
        except Exception as e:
            raise CameraError(f"Camera initialization failed: {e}")
    
    async def _initialize_audio(self) -> None:
        """Initialize audio system"""
        try:
            if PYGAME_AVAILABLE:
                pygame.mixer.init()
                
                # Try to load audio file
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                audio_path = os.path.join(base_dir, "static", "music.wav")
                
                if os.path.exists(audio_path):
                    pygame.mixer.music.load(audio_path)
                    self.audio_initialized = True
                    logger.info("Audio system initialized successfully")
                else:
                    logger.warning(f"Audio file not found: {audio_path}")
            else:
                logger.info("Pygame not available - audio alerts disabled")
                self.audio_initialized = False
                
        except Exception as e:
            logger.warning(f"Audio initialization failed: {e}")
            self.audio_initialized = False
            # Don't raise exception - audio is not critical
    
    async def _monitoring_loop(
        self,
        driver_profile: DriverProfile,
        settings: Dict[str, Any]
    ) -> None:
        """
        Main monitoring loop
        Args:
            driver_profile: Driver profile instance
            settings: Detection settings
        """
        ear_threshold = settings.get('ear_threshold', 0.3)
        ear_frames = settings.get('ear_frames', 30)
        yawn_threshold = settings.get('yawn_threshold', 20)
        
        while self.is_running:
            try:
                # Read frame
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    logger.warning("No frame received from camera")
                    await asyncio.sleep(0.1)
                    continue
                
                # Resize frame for better performance
                frame = cv2.resize(frame, (640, 480))
                
                # Perform detection
                is_drowsy, is_yawning, annotated_frame = self.detector.detect_drowsiness(frame)
                
                # Handle drowsiness detection
                if is_drowsy:
                    self.consecutive_drowsy_frames += 1
                    if self.consecutive_drowsy_frames >= ear_frames:
                        await self._handle_drowsiness_alert(driver_profile)
                        self.consecutive_drowsy_frames = 0  # Reset after alert
                else:
                    self.consecutive_drowsy_frames = 0
                
                # Handle yawn detection
                if is_yawning:
                    self.consecutive_yawn_frames += 1
                    if self.consecutive_yawn_frames >= 3:  # Lower threshold for yawning
                        await self._handle_yawn_alert(driver_profile)
                        self.consecutive_yawn_frames = 0  # Reset after alert
                else:
                    self.consecutive_yawn_frames = 0
                
                # Display frame
                cv2.imshow("DrowsiSense - Driver Monitoring", annotated_frame)
                
                # Check for quit key
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                
                # Control frame rate
                await asyncio.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause before continuing
    
    async def _handle_drowsiness_alert(self, driver_profile: DriverProfile) -> None:
        """Handle drowsiness detection"""
        try:
            # Create alert
            alert = await alert_service.create_alert(
                driver_profile=driver_profile,
                alert_type='drowsiness',
                description='Drowsiness detected!',
                severity='high',
                confidence=0.9
            )
            
            # Play audio alert
            await self._play_audio_alert()
            
            # Send email alert
            await alert_service.send_email_alert(
                alert=alert,
                recipient_email=driver_profile.user.email
            )
            
            logger.info("Drowsiness alert processed successfully")
            
        except Exception as e:
            logger.error(f"Error handling drowsiness alert: {e}")
    
    async def _handle_yawn_alert(self, driver_profile: DriverProfile) -> None:
        """Handle yawn detection"""
        try:
            # Create alert
            alert = await alert_service.create_alert(
                driver_profile=driver_profile,
                alert_type='yawning',
                description='Excessive yawning detected!',
                severity='medium',
                confidence=0.8
            )
            
            # Play audio alert
            await self._play_audio_alert()
            
            logger.info("Yawn alert processed successfully")
            
        except Exception as e:
            logger.error(f"Error handling yawn alert: {e}")
    
    async def _play_audio_alert(self) -> None:
        """Play audio alert"""
        try:
            if self.audio_initialized and PYGAME_AVAILABLE:
                pygame.mixer.music.play()
            else:
                logger.info("Audio alert skipped - pygame not available")
            
            # Optional: Text-to-speech
            await self._play_tts_alert()
            
        except Exception as e:
            logger.warning(f"Audio alert failed: {e}")
    
    async def _play_tts_alert(self) -> None:
        """Play text-to-speech alert"""
        try:
            import os
            if os.name == 'nt':  # Windows
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.say("Alert: Drowsiness detected!")
                    engine.runAndWait()
                except ImportError:
                    logger.debug("pyttsx3 not available")
            else:  # Linux/Mac
                await sync_to_async(os.system)('espeak "Alert: Drowsiness detected!"')
                
        except Exception as e:
            logger.debug(f"TTS failed: {e}")


# Factory function
def create_detection_engine() -> DetectionEngine:
    """Create a new detection engine instance"""
    return DetectionEngine()