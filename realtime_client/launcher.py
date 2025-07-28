import asyncio
from realtime_client.conversation import ConversationManager

### CONFIGURATION ###
CONVERSATION_DURATION_SECONDS = 60 # hoeveelheid seconden dat het gesprek maximaal duurt
PROXY_URL = "wss://33da-134-221-46-142.ngrok-free.app/ws/chat" # server endpoint waar ik de proxy opzet
PROXY_URL_2 = "wss://57e7b0ed6800.ngrok-free.app/ws/chat"
# "wss://a00ccb94098a.ngrok-free.app/ws/chat"
async def main():
    """
    Dit is een voorbeeld van hoe jullie ConversationManager moeten aanroepen. 
    """

    ### JULLIE CODE ###

    print("ConversationManager is starting a conversation.")

    def show_transcript(text: str):
        print(f"Transcript: {text}", end='\r')

    # Dit is de enige functie die jullie moeten aanroepen.
    await ConversationManager.start_proxied_conversation(
        proxy_url=PROXY_URL_2,
        duration_seconds=CONVERSATION_DURATION_SECONDS,
        on_transcript_update=show_transcript,
    )

    print("\nConversationManager is done.")

    ### JULLIE CODE ###

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nlauncher interrupted by user.")
    except Exception as e:
        print(f"an unexpected error occurred in the launcher: {e}")