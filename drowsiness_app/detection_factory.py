"""
Detection Factory - automatically chooses the best available detection method
Fallback order: dlib -> MediaPipe -> basic OpenCV
"""
import logging

logger = logging.getLogger(__name__)

class DetectionFactory:
    """Factory to create the best available detector"""
    
    @staticmethod
    def create_detector():
        """Create the best available detector"""
        
        # Check if we're in production environment
        import os
        if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('production'):
            logger.info("Using production detector for Railway deployment")
            from .detection_production import get_production_detector
            return get_production_detector()
        
        # Try dlib first (original implementation - for local development)
        try:
            import dlib
            from .original_detection import DlibDrowsinessDetector  # We'll create this
            logger.info("Using dlib-based detection")
            return DlibDrowsinessDetector()
        except ImportError:
            logger.warning("dlib not available, trying MediaPipe")
            
        # Try MediaPipe
        try:
            from .mediapipe_detection import MediaPipeDrowsinessDetector
            logger.info("Using MediaPipe-based detection")
            return MediaPipeDrowsinessDetector()
        except ImportError:
            logger.warning("MediaPipe not available, using production detector")
            
        # Fallback to production detector
        try:
            from .detection_production import get_production_detector
            logger.info("Using production detector as fallback")
            return get_production_detector()
        except ImportError:
            logger.error("No detection methods available!")
            raise ImportError("No computer vision libraries available for detection")

# Convenience function
def get_detector():
    """Get a detector instance"""
    return DetectionFactory.create_detector()