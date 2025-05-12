
# Vocode Quickstart

This project uses [Vocode](https://docs.vocode.dev/) to create a real-time voice bot.

## 🐍 Requirements

- Python 3.8 or newer
- `pip` package manager

## 📦 Installation

1. **Clone the repo** (or download `quickstart.py`):
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo

2. **Install required packages**:

   ```bash
   pip install vocode openai
   ```

   > 📝 You may also need `python-dotenv` if you want to use a `.env` file:

   ```bash
   pip install python-dotenv
   ```

3. **Set up environment variables**:

   You must set the following variables to use Azure Speech and OpenAI:

   ```
   AZURE_SPEECH_KEY=your_azure_speech_key
   AZURE_SPEECH_REGION=your_azure_region
   AZURE_DEPLOYMENT_NAME=your_deployment_name

   OPENAI_API_TYPE=azure
   OPENAI_API_BASE=https://your-openai-resource.openai.azure.com/
   OPENAI_API_VERSION=2023-05-15
   OPENAI_API_KEY=your_openai_key
   OPENAI_MODEL_NAME=your_model_name
   ```

   You can set them in your terminal:

   ```bash
   export AZURE_SPEECH_KEY=your_azure_speech_key
   export AZURE_SPEECH_REGION=your_azure_region
   export AZURE_DEPLOYMENT_NAME=your_deployment_name
   export OPENAI_API_TYPE=azure
   export OPENAI_API_BASE=https://your-openai-resource.openai.azure.com/
   export OPENAI_API_VERSION=2023-05-15
   export OPENAI_API_KEY=your_openai_key
   export OPENAI_MODEL_NAME=your_model_name
   ```

   Or put them in a `.env` file for automatic loading:

   ```
   # .env
   AZURE_SPEECH_KEY=your_azure_speech_key
   AZURE_SPEECH_REGION=your_azure_region
   AZURE_DEPLOYMENT_NAME=your_deployment_name

   OPENAI_API_TYPE=azure
   OPENAI_API_BASE=https://your-openai-resource.openai.azure.com/
   OPENAI_API_VERSION=2023-05-15
   OPENAI_API_KEY=your_openai_key
   OPENAI_MODEL_NAME=your_model_name
   ```

## 🚀 Run the Bot

```bash
python quickstart.py
```

Your voice bot should now start and interact with you in real time.

## 📚 More Info

See the full guide here:
[Vocode Python Quickstart](https://docs.vocode.dev/open-source/python-quickstart)


