import os
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from google.cloud import firestore
import json

class LangChainConversationManager:
    def __init__(self):
        self.db = firestore.Client()
        
    def get_conversation_memory(self, sender_email: str) -> ConversationBufferMemory:
        try:
            doc_ref = self.db.collection('conversations').document(sender_email)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                messages = []
                for msg in (data or {}).get('messages', []):
                    if msg['type'] == 'human':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['type'] == 'ai':
                        messages.append(AIMessage(content=msg['content']))
                
                memory = ConversationBufferMemory(return_messages=True)
                memory.chat_memory.messages = messages
                return memory
            else:
                return ConversationBufferMemory(return_messages=True)
                
        except Exception as e:
            print(f"Error getting conversation memory: {e}")
            return ConversationBufferMemory(return_messages=True)
    
    def save_conversation(self, sender_email: str, memory: ConversationBufferMemory):
        try:
            messages = []
            for msg in memory.chat_memory.messages:
                if isinstance(msg, HumanMessage):
                    messages.append({'type': 'human', 'content': msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({'type': 'ai', 'content': msg.content})
            
            doc_ref = self.db.collection('conversations').document(sender_email)
            doc_ref.set({
                'email': sender_email,
                'messages': messages,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def add_message(self, sender_email: str, message: str, is_human: bool = True):
        memory = self.get_conversation_memory(sender_email)
        
        if is_human:
            memory.chat_memory.add_user_message(message)
        else:
            memory.chat_memory.add_ai_message(message)
        
        self.save_conversation(sender_email, memory)
        return memory
    
    def get_conversation_context(self, sender_email: str) -> str:
        memory = self.get_conversation_memory(sender_email)
        
        if not memory.chat_memory.messages:
            return ""
        
        context = "PREVIOUS CONVERSATION HISTORY:\n"
        for msg in memory.chat_memory.messages[-6:]:
            if isinstance(msg, HumanMessage):
                context += f"\nTenant: {msg.content[:200]}...\n"
            elif isinstance(msg, AIMessage):
                context += f"Pandora: {msg.content[:200]}...\n"
        
        return context
    
    def clear_conversation(self, sender_email: str):
        try:
            doc_ref = self.db.collection('conversations').document(sender_email)
            doc_ref.delete()
            print(f"Cleared conversation history for {sender_email}")
        except Exception as e:
            print(f"Error clearing conversation: {e}")
    
    def get_conversation_summary(self, sender_email: str) -> dict:
        try:
            memory = self.get_conversation_memory(sender_email)
            messages = memory.chat_memory.messages
            
            return {
                'email': sender_email,
                'total_messages': len(messages),
                'human_messages': len([m for m in messages if isinstance(m, HumanMessage)]),
                'ai_messages': len([m for m in messages if isinstance(m, AIMessage)]),
                'last_message': messages[-1].content if messages else None
            }
        except Exception as e:
            print(f"Error getting conversation summary: {e}")
            return {} 