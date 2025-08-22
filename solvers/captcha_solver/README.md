# Unified Captcha Solver API

A comprehensive, API-based captcha solver that handles both **Cloudflare Turnstile** and **hCaptcha** challenges using AI models for image recognition.

## 🚀 Features

### Supported Captcha Types
- **Cloudflare Turnstile**: Automatic solving with browser automation
- **hCaptcha Grid Challenges**: AI-powered image recognition for grid-based selection tasks

### AI Models Integration
- **Google Gemini** (gemini-1.5-flash) - Free tier available
- **Together AI** (Llama-3.2-11B-Vision-Instruct-Turbo) - Free tier available  
- **OpenAI** (gpt-4o-mini) - Paid service
- Automatic fallback between models for reliability

### Browser Support
- **Camoufox** (recommended) - Anti-detection browser
- **Chromium/Chrome** - Standard browsers
- **Microsoft Edge** - Alternative option

## 📋 Requirements

### System Dependencies
```bash
# Install system packages (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv

# For VNC integration (optional)
sudo apt-get install -y x11vnc xvfb fluxbox
```

### Python Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `quart` - Async web framework
- `hypercorn` - ASGI server
- `aiohttp` - HTTP client for AI APIs
- `pillow` - Image processing
- `playwright` - Browser automation
- `camoufox` - Anti-detection browser (optional)

## 🔧 Installation

1. **Clone and setup**:
```bash
cd solvers/captcha_solver
pip install -r requirements.txt
```

2. **Install browsers**:
```bash
# Install Playwright browsers
playwright install chromium

# Install Camoufox (recommended)
pip install camoufox[geoip]
```

3. **Configure AI models** (optional but recommended):
```bash
# Set environment variables for AI models
export GEMINI_API_KEY="your_gemini_api_key"
export TOGETHER_API_KEY="your_together_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

## 🚀 Usage

### Starting the Server

**Basic startup**:
```bash
python start_solver.py
```

**Advanced options**:
```bash
python start_solver.py \
  --host 0.0.0.0 \
  --port 5000 \
  --browser camoufox \
  --threads 4 \
  --debug
```

**Command line options**:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 5000)
- `--headless`: Run browsers in headless mode
- `--browser`: Browser type (camoufox, chromium, chrome, msedge)
- `--threads`: Number of browser threads (default: 2)
- `--debug`: Enable debug mode
- `--useragent`: Custom user agent string
- `--proxy-support`: Enable proxy support

### API Endpoints

#### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "browser_pool_size": 2,
  "active_tasks": 0
}
```

#### Turnstile Solver

**Submit task**:
```bash
GET /turnstile?url=https://example.com&sitekey=0x4AAAAAAADnPIDROlWd_wc
```

**Optional parameters**:
- `action`: Action parameter
- `cdata`: CData parameter  
- `pagedata`: Page data parameter

**Response**:
```json
{
  "task_id": "uuid-here"
}
```

**Get results**:
```bash
GET /results?id=task_id
```

**Response**:
```json
{
  "status": "ready",
  "solution": "turnstile_response_token",
  "elapsed_time": 12.34
}
```

#### hCaptcha Solver

**Submit task**:
```bash
POST /hcaptcha
Content-Type: application/json

{
  "images": ["base64_image1", "base64_image2", ...],
  "instructions": "Click all the objects that fit inside the sample item",
  "rows": 3,
  "columns": 3
}
```

**Response**:
```json
{
  "task_id": "uuid-here"
}
```

**Get results**:
```bash
GET /resolved?id=task_id
```

**Response**:
```json
{
  "status": "ready",
  "solution": [1, 4, 7]
}
```

### Status Codes

- `200`: Success - Task completed
- `202`: Accepted - Task queued/processing
- `400`: Bad Request - Invalid parameters
- `500`: Server Error - Processing failed

### Task Status Values

- `not_ready`: Task is still processing
- `ready`: Task completed successfully
- `error`: Task failed with error

## 🤖 AI Model Configuration

### Google Gemini
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set environment variable: `export GEMINI_API_KEY="your_key"`

### Together AI
1. Get API key from [Together AI](https://api.together.xyz/)
2. Set environment variable: `export TOGETHER_API_KEY="your_key"`

### OpenAI
1. Get API key from [OpenAI](https://platform.openai.com/api-keys)
2. Set environment variable: `export OPENAI_API_KEY="your_key"`

## 🧪 Testing

### Run Tests
```bash
# Test all functionality
python test_solver.py

# Test specific components
python test_solver.py --test health
python test_solver.py --test turnstile
python test_solver.py --test hcaptcha

# Test against different server
python test_solver.py --url http://localhost:8080
```

### Manual Testing

**Test Turnstile**:
```bash
curl "http://localhost:5000/turnstile?url=https://demo.turnstile.workers.dev/&sitekey=0x4AAAAAAADnPIDROlWd_wc"
```

**Test hCaptcha**:
```bash
curl -X POST http://localhost:5000/hcaptcha \
  -H "Content-Type: application/json" \
  -d '{
    "images": ["base64_encoded_image"],
    "instructions": "Select all vehicles",
    "rows": 3,
    "columns": 3
  }'
```

## 🖥️ VNC Integration

The solver supports VNC integration for visual monitoring:

1. **Install VNC components**:
```bash
sudo apt-get install x11vnc xvfb fluxbox websockify
```

2. **Start with VNC**:
```bash
export USE_VNC=true
python start_solver.py --browser camoufox
```

3. **Access via noVNC**:
- Individual sessions: `http://localhost:6080/vnc.html`
- Web interface: `http://localhost:8080`

## 📊 Performance & Limits

### Image Requirements (hCaptcha)
- **Formats**: JPEG, PNG, GIF
- **Max file size**: 600 KB per image
- **Max dimensions**: 1000px on any side
- **Grid sizes**: 3x3, 4x4, 5x5 supported

### AI Model Limits
- **Gemini**: 16 images max per request
- **Together AI**: 8 images max per request  
- **OpenAI**: 10 images max per request

### Performance Tips
- Use multiple browser threads for concurrent solving
- Enable caching for repeated challenges
- Use Camoufox for better anti-detection
- Set appropriate timeouts for your use case

## 🔧 Configuration

### Environment Variables
```bash
# AI Model APIs
GEMINI_API_KEY=your_gemini_key
TOGETHER_API_KEY=your_together_key
OPENAI_API_KEY=your_openai_key

# VNC Integration
USE_VNC=true
VNC_BASE_DISPLAY=10
VNC_BASE_PORT=5900
VNC_BASE_WEBSOCKET_PORT=6080

# Logging
LOG_LEVEL=INFO
DEBUG_MODE=false
```

### Browser Configuration
```python
# Custom browser args
browser_args = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--window-size=1920,1080'
]
```

## 🚨 Error Handling

### Common Errors

**Browser initialization failed**:
- Install required browsers: `playwright install chromium`
- Check system dependencies
- Verify display availability for non-headless mode

**AI model API errors**:
- Verify API keys are set correctly
- Check API quotas and limits
- Ensure network connectivity

**Image processing errors**:
- Verify image format (JPEG, PNG, GIF)
- Check image size limits (600KB, 1000px)
- Validate base64 encoding

### Debugging

Enable debug mode:
```bash
python start_solver.py --debug
```

Check logs:
```bash
tail -f captcha_solver.log
```

## 🔒 Security Considerations

- **API Keys**: Store securely, never commit to version control
- **Network**: Use HTTPS in production
- **Rate Limiting**: Implement appropriate rate limits
- **Input Validation**: All inputs are validated and sanitized
- **Browser Security**: Browsers run in sandboxed environments

## 📈 Monitoring

### Health Monitoring
```bash
# Check server health
curl http://localhost:5000/health

# Monitor active tasks
curl http://localhost:5000/health | jq '.active_tasks'
```

### Performance Metrics
- Task completion times
- Success/failure rates
- AI model performance
- Browser pool utilization

## 🤝 Integration Examples

### Python Client
```python
import aiohttp
import asyncio

async def solve_turnstile(url, sitekey):
    async with aiohttp.ClientSession() as session:
        # Submit task
        async with session.get(f'http://localhost:5000/turnstile', 
                              params={'url': url, 'sitekey': sitekey}) as resp:
            data = await resp.json()
            task_id = data['task_id']
        
        # Poll for results
        while True:
            await asyncio.sleep(2)
            async with session.get(f'http://localhost:5000/results', 
                                  params={'id': task_id}) as resp:
                data = await resp.json()
                if data['status'] == 'ready':
                    return data['solution']
                elif data['status'] == 'error':
                    raise Exception(data['error'])
```

### JavaScript Client
```javascript
async function solveTurnstile(url, sitekey) {
    // Submit task
    const response = await fetch(`http://localhost:5000/turnstile?url=${url}&sitekey=${sitekey}`);
    const { task_id } = await response.json();
    
    // Poll for results
    while (true) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const resultResponse = await fetch(`http://localhost:5000/results?id=${task_id}`);
        const result = await resultResponse.json();
        
        if (result.status === 'ready') {
            return result.solution;
        } else if (result.status === 'error') {
            throw new Error(result.error);
        }
    }
}
```

## 📝 License

This project is part of the Exo-Mass captcha solving system. Use responsibly and in accordance with the terms of service of the websites you're interacting with.

## 🆘 Support

For issues and questions:
1. Check the logs for error details
2. Verify all dependencies are installed
3. Test with the provided test script
4. Check API key configuration for AI models

---

**Note**: This solver is designed to work as a separate service from your main application. It provides a clean API interface for captcha solving without tight coupling to your existing codebase.