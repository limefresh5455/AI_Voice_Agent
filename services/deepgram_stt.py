"""
Deepgram Speech-to-Text (STT) service.
Real-time streaming transcription with low latency.
NOTE: Compatible with Deepgram SDK v5.3.0+
"""

import asyncio
import logging
import os
import certifi
from typing import AsyncIterator, Optional, Callable
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV1SocketClientResponse, ListenV1MediaMessage
from config import settings

# Configure SSL certificates for macOS
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

logger = logging.getLogger(__name__)


class DeepgramSTTService:
    """
    Deepgram real-time speech-to-text service using SDK v5.3.0+
    
    Features:
    - Streaming transcription
    - Low latency (~300ms)
    - Automatic punctuation
    - Interim results for responsiveness
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.deepgram_api_key
        self.client = AsyncDeepgramClient(api_key=self.api_key)
        self.connection = None
        self._connection_context = None
        self._listen_task = None
        self.transcript_callback: Optional[Callable[[str, bool], None]] = None
        logger.info("Deepgram STT service initialized")
    
    async def start_stream(
        self,
        on_transcript: Callable[[str, bool], None],
        language: str = "en-US",
        ) -> None:
        """
        Start streaming transcription using Deepgram SDK v5.3.0+ API.
        
        Args:
            on_transcript: Callback function(text: str, is_final: bool)
            language: Language code (default: en-US)
        """
        try:
            self.transcript_callback = on_transcript
            
            # Connect using v5+ API (context manager)
            self._connection_context = self.client.listen.v1.connect(
                model="nova-2",
                encoding="linear16",
                sample_rate=16000,
                interim_results=True,
                smart_format=True,
                punctuate=True,
                endpointing=100
            )
            
            self.connection = await self._connection_context.__aenter__()
            
            # Set up event handlers
            self.connection.on(EventType.MESSAGE, self._handle_message)
            self.connection.on(EventType.ERROR, lambda error: logger.error(f"Deepgram error: {error}"))
            self.connection.on(EventType.CLOSE, lambda _: logger.info("Deepgram connection closed"))
            
            # Start listening in background
            self._listen_task = asyncio.create_task(self.connection.start_listening())
            
            logger.info("Deepgram STT stream started")
                
        except Exception as e:
            logger.error(f"Error starting Deepgram STT: {e}")
            raise
    
    async def send_audio(self, audio_chunk: bytes) -> None:
        """
        Send audio chunk to Deepgram for transcription.
        
        Args:
            audio_chunk: PCM audio data (16kHz, 16-bit, mono)
        """
        if self.connection:
            try:
                # SDK v5+: send media message
                await self.connection.send_media(ListenV1MediaMessage(audio_chunk))
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")
    
    def _handle_message(self, message: ListenV1SocketClientResponse):
        """Handle messages from Deepgram (v5+ SDK format)."""
        try:
            # Check message type
            msg_type = getattr(message, 'type', 'Unknown')
            
            if msg_type == 'Results':
                # Extract transcript
                if hasattr(message, 'channel'):
                    channel = message.channel
                    if hasattr(channel, 'alternatives') and len(channel.alternatives) > 0:
                        text = channel.alternatives[0].transcript
                        
                        if len(text) == 0:
                            return
                        
                        is_final = message.is_final if hasattr(message, 'is_final') else False
                        
                        # Call the callback
                        if self.transcript_callback:
                            asyncio.create_task(self.transcript_callback(text, is_final))
                        
                        if is_final:
                            logger.info(f"Final transcript: {text}")
                        else:
                            logger.debug(f"Interim transcript: {text}")
                        
        except Exception as e:
            logger.error(f"Error processing Deepgram message: {e}")
    
    async def close(self) -> None:
        """Close Deepgram connection."""
        # Cancel listen task
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        # Close the connection context
        if self._connection_context:
            try:
                await self._connection_context.__aexit__(None, None, None)
                logger.info("Deepgram STT stream closed")
            except Exception as e:
                logger.warning(f"Error closing Deepgram connection: {e}")
            finally:
                self.connection = None
                self._connection_context = None
