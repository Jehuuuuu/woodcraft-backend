import requests 
import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def poll_task_status(task_id, max_retries=100, initial_delay=3, backoff_factor=2):
    API_KEY = os.getenv('API_KEY')
    if not API_KEY:
        logger.error("API_KEY environment variable not set")
        return None

    url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    current_delay = initial_delay
    for attempt in range(max_retries):
        try:
            # Make API call to check status
            response = requests.get(url, headers=headers, timeout=30)
            if not response.ok:
                logger.warning(f"API error (attempt {attempt + 1}/{max_retries}): HTTP {response.status_code}")
                continue

            response_data = response.json()
            task_data = response_data.get('data', {})
            status = task_data.get('status')

            if status == "success":
                logger.info(f"Task {task_id} completed successfully")
                return task_data
            
            elif status in ["failed", "error"]:
                logger.error(f"Task {task_id} failed with status: {status}")
                return None
            
            if status in ["queued", "running"]:
                logger.info(f"Task {task_id} {status} (attempt {attempt + 1}/{max_retries})")
                time.sleep(current_delay)
                current_delay *= backoff_factor  
                continue

            logger.error(f"Unexpected task status: {status}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Polling error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            time.sleep(current_delay)
            current_delay *= backoff_factor

    logger.error(f"Polling timeout after {max_retries} attempts")
    return None

def generate_3d_model(design_prompt, material, dimensions=None, generation_type='text_to_model', preview_task_id=None):
    API_KEY = os.getenv('API_KEY')
    url = "https://api.tripo3d.ai/v2/openapi/task"

    if not API_KEY:
        logger.error("API_KEY environment variable not set")
        return None
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Determine payload based on mode
    if generation_type == 'text_to_model':
        # Prepare the prompt with material and dimensions if provided
        enhanced_prompt = f"A {material} wooden {design_prompt}"
        if dimensions:
            enhanced_prompt += f" with dimensions: {dimensions.get('length', 0)}x{dimensions.get('width', 0)}x{dimensions.get('thickness', 0)} inches"
        
        payload = {
            "type": generation_type,
            "prompt": enhanced_prompt,
        }
    elif generation_type == 'refine':
        enhanced_prompt = f"A {material} wooden {design_prompt}"
        if dimensions:
            enhanced_prompt += f" with dimensions: {dimensions.get('length', 0)}x{dimensions.get('width', 0)}x{dimensions.get('thickness', 0)} inches"
        
        payload = {
            "type": "refine",
            "preview_task_id": preview_task_id,
            "prompt": enhanced_prompt,
        }
    else:
        logger.error(f"Unsupported mode: {generation_type}")
        return None

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            task_id = response_data.get('data', {}).get('task_id')
            if not task_id:
                logger.error("No task ID in response")
                return None

            final_data = poll_task_status(task_id)
            if not final_data or final_data.get('status') != 'success':
                return None

            return {
                'task_id': task_id,
                'status': final_data.get('status'),
                'rendered_model': final_data.get('output', {}).get('pbr_model', {}),
                'thumbnail': final_data.get('thumbnail')
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 503:
                logger.warning(f"Retrying... (attempt {attempt + 1}/3)")
                time.sleep(10 * (attempt + 1))
            else:
                logger.error(f"HTTP error: {str(e)}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return None

    return None

