from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

beat_tracker = None

def initialize_beat_tracker():
    global beat_tracker
    if beat_tracker is None:
        try:
            logger.info("Attempting to import File2Beats...")
            from beat_this.inference import File2Beats
            logger.info("File2Beats imported successfully")
            beat_tracker = File2Beats(device="cpu")
            logger.info("Beat tracker initialized successfully")
        except ImportError as e:
            logger.error(f"Import failed: {e}")
            raise Exception(f"Failed to import beat_this: {e}")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise Exception(f"Failed to initialize beat tracker: {e}")
    return beat_tracker

@app.route('/health', methods=['GET'])
def health_check():
    try:
        initialize_beat_tracker()
        return jsonify({'status': 'healthy', 'message': 'Beat This! server is running'})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/detect-beats', methods=['POST'])
def detect_beats():
    logger.info("Received beat detection request")
    try:
        if 'audio' not in request.files:
            logger.error("No audio file in request")
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        logger.info(f"Processing file: {audio_file.filename}")
        
        if audio_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        tracker = initialize_beat_tracker()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            logger.info("Starting beat detection...")
            beats, downbeats = tracker(tmp_path)
            logger.info(f"Detection complete: {len(beats)} beats, {len(downbeats)} downbeats")
            
            beats_list = beats.tolist() if hasattr(beats, 'tolist') else list(beats)
            downbeats_list = downbeats.tolist() if hasattr(downbeats, 'tolist') else list(downbeats)
            
            return jsonify({
                'success': True,
                'beats': beats_list,
                'downbeats': downbeats_list,
                'counts': {
                    'beats': len(beats_list),
                    'downbeats': len(downbeats_list)
                }
            })
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        logger.error(f"Beat detection error: {e}")
        return jsonify({'error': f'Beat detection failed: {str(e)}'}), 500

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Server is responding!'})

if __name__ == '__main__':
    print("=== Starting Beat This! Server ===")
    print("Server will run on: http://localhost:5000")
    print("Test the server by visiting: http://localhost:5000/test")
    print("Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=5000, debug=True)