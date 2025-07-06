import json
import os
from typing import List, Dict, Any
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UmrahRAGSystem:
    def __init__(self, api_key: str):
        """Initialize the RAG system with embeddings and vector store"""
        self.api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
        
        # Initialize embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        
        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
    
    def load_scraped_data(self, filename="umrah_scraped_data.json"):
        """Load scraped data from JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"File {filename} not found. Please run scraper.py first.")
            return None
    
    def process_rituals_data(self, rituals_data: List[Dict]) -> List[Document]:
        """Process ritual data into documents"""
        documents = []
        
        for ritual in rituals_data:
            # Create main document
            content = f"Ritual Section: {ritual['section']}\n"
            content += f"Title: {ritual['title']}\n"
            content += f"Content: {ritual['content']}\n"
            
            # Add sub-sections
            for sub in ritual.get('sub_sections', []):
                content += f"\n{sub['heading']}:\n"
                content += "\n".join(sub['content'])
            
            metadata = {
                "source": "nusuk_rituals",
                "section": ritual['section'],
                "url": ritual['url'],
                "type": "ritual_guide"
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def process_destination_data(self, destinations_data: List[Dict]) -> List[Document]:
        """Process destination data into documents"""
        documents = []
        
        for dest in destinations_data:
            city = dest['city']
            
            for section in dest['sections']:
                content = f"City: {city.title()}\n"
                content += f"Section: {section['section']}\n"
                content += f"Content: {section['content']}\n"
                
                metadata = {
                    "source": "nusuk_destinations",
                    "city": city,
                    "section": section['section'],
                    "url": section['url'],
                    "type": "destination_info"
                }
                
                documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def process_hotel_data(self, hotels_data: List[Dict]) -> List[Document]:
        """Process hotel data into documents"""
        documents = []
        
        for hotel in hotels_data:
            content = f"Hotel: {hotel['name']}\n"
            content += f"City: {hotel['city'].title()}\n"
            content += f"Area: {hotel['area']}\n"
            content += f"Stars: {hotel['stars']}\n"
            content += f"Distance to Haram: {hotel['distance_to_haram']}\n"
            content += f"Price: {hotel['price']}\n"
            content += f"Room Types: {', '.join(hotel['room_types'])}\n"
            content += f"Amenities: {', '.join(hotel['amenities'])}\n"
            
            metadata = {
                "source": hotel['source'],
                "city": hotel['city'],
                "stars": hotel['stars'],
                "area": hotel['area'],
                "type": "hotel",
                "has_kaaba_view": "Kaaba view" in hotel['room_types'],
                "has_haram_view": "Haram view" in hotel['room_types'],
                "walking_distance": "walking distance" in hotel['room_types'],
                "has_shuttle": "shuttle" in hotel['room_types']
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def process_reddit_data(self, reddit_data: List[Dict]) -> List[Document]:
        """Process Reddit reviews into documents"""
        documents = []
        
        for post in reddit_data:
            content = f"Reddit Review - {post['title']}\n"
            content += f"Subreddit: r/{post['subreddit']}\n"
            content += f"Score: {post['score']}\n"
            content += f"Content: {post['content']}\n"
            
            metadata = {
                "source": "reddit",
                "subreddit": post['subreddit'],
                "score": post['score'],
                "created": post['created'],
                "url": post['url'],
                "type": "user_review",
                "search_term": post['search_term']
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def create_vector_store(self, documents: List[Document]):
        """Create FAISS vector store from documents"""
        logger.info(f"Creating vector store with {len(documents)} documents...")
        
        # Split documents into chunks
        split_docs = []
        for doc in documents:
            chunks = self.text_splitter.split_documents([doc])
            split_docs.extend(chunks)
        
        logger.info(f"Split into {len(split_docs)} chunks")
        
        # Create vector store
        self.vector_store = FAISS.from_documents(
            documents=split_docs,
            embedding=self.embeddings
        )
        
        logger.info("Vector store created successfully!")
    
    def save_vector_store(self, path="vector_store"):
        """Save vector store to disk"""
        if self.vector_store:
            self.vector_store.save_local(path)
            logger.info(f"Vector store saved to {path}")
    
    def load_vector_store(self, path="vector_store"):
        """Load vector store from disk"""
        try:
            self.vector_store = FAISS.load_local(path, self.embeddings)
            logger.info(f"Vector store loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False
    
    def build_rag_system(self):
        """Build the complete RAG system"""
        # Load scraped data
        data = self.load_scraped_data()
        if not data:
            return False
        
        # Process all data types
        all_documents = []
        
        # Process rituals
        if data.get('rituals'):
            ritual_docs = self.process_rituals_data(data['rituals'])
            all_documents.extend(ritual_docs)
            logger.info(f"Processed {len(ritual_docs)} ritual documents")
        
        # Process destinations
        if data.get('destinations'):
            dest_docs = self.process_destination_data(data['destinations'])
            all_documents.extend(dest_docs)
            logger.info(f"Processed {len(dest_docs)} destination documents")
        
        # Process hotels
        if data.get('hotels'):
            hotel_docs = self.process_hotel_data(data['hotels'])
            all_documents.extend(hotel_docs)
            logger.info(f"Processed {len(hotel_docs)} hotel documents")
        
        # Process Reddit reviews
        if data.get('reddit_reviews'):
            reddit_docs = self.process_reddit_data(data['reddit_reviews'])
            all_documents.extend(reddit_docs)
            logger.info(f"Processed {len(reddit_docs)} Reddit documents")
        
        # Create vector store
        self.create_vector_store(all_documents)
        
        # Save vector store
        self.save_vector_store()
        
        return True
    
    def query(self, question: str, k: int = 5, filter_dict: Dict = None) -> Dict[str, Any]:
        """Query the RAG system"""
        if not self.vector_store:
            return {"error": "Vector store not initialized"}
        
        # Perform similarity search with optional filtering
        if filter_dict:
            docs = self.vector_store.similarity_search(
                question, 
                k=k,
                filter=filter_dict
            )
        else:
            docs = self.vector_store.similarity_search(question, k=k)
        
        # Format context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Create prompt
        prompt = f"""Based on the following context about Umrah, hotels, and destinations, 
        please answer the question accurately and helpfully.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:"""
        
        # Get response from LLM
        response = self.llm.invoke(prompt).content
        
        # Return response with sources
        return {
            "answer": response,
            "sources": [
                {
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata
                } for doc in docs
            ]
        }
    
    def query_hotels(self, city: str = None, stars: int = None, 
                    has_kaaba_view: bool = None, walking_distance: bool = None) -> List[Dict]:
        """Query hotels with specific filters"""
        filter_dict = {"type": "hotel"}
        
        if city:
            filter_dict["city"] = city.lower()
        if stars:
            filter_dict["stars"] = stars
        if has_kaaba_view is not None:
            filter_dict["has_kaaba_view"] = has_kaaba_view
        if walking_distance is not None:
            filter_dict["walking_distance"] = walking_distance
        
        question = f"Find hotels in {city or 'any city'}"
        if stars:
            question += f" with {stars} stars"
        if has_kaaba_view:
            question += " with Kaaba view"
        if walking_distance:
            question += " within walking distance to Haram"
        
        return self.query(question, k=10, filter_dict=filter_dict)
    
    def query_rituals(self, ritual_name: str) -> Dict[str, Any]:
        """Query specific ritual information"""
        filter_dict = {"type": "ritual_guide"}
        return self.query(f"Explain the {ritual_name} ritual in detail", filter_dict=filter_dict)
    
    def query_attractions(self, city: str, category: str = None) -> Dict[str, Any]:
        """Query attractions and destinations"""
        filter_dict = {
            "type": "destination_info",
            "city": city.lower()
        }
        
        if category:
            question = f"What are the {category} options in {city}?"
        else:
            question = f"What are the main attractions and services in {city}?"
        
        return self.query(question, filter_dict=filter_dict)

# Utility function to initialize RAG in Streamlit
@st.cache_resource
def initialize_rag_system(api_key: str):
    """Initialize and cache the RAG system"""
    rag = UmrahRAGSystem(api_key)
    
    # Try to load existing vector store
    if not rag.load_vector_store():
        # Build from scratch if not found
        logger.info("Building RAG system from scratch...")
        if rag.build_rag_system():
            logger.info("RAG system built successfully!")
        else:
            logger.error("Failed to build RAG system")
            return None
    
    return rag

if __name__ == "__main__":
    # Test the RAG system
    api_key = os.getenv("GOOGLE_API_KEY", "your-api-key-here")
    rag = UmrahRAGSystem(api_key)
    
    # Build the system
    if rag.build_rag_system():
        print("RAG system built successfully!")
        
        # Test queries
        print("\n--- Testing Ritual Query ---")
        result = rag.query_rituals("tawaf")
        print(f"Answer: {result['answer'][:200]}...")
        
        print("\n--- Testing Hotel Query ---")
        result = rag.query_hotels(city="makkah", has_kaaba_view=True)
        print(f"Answer: {result['answer'][:200]}...")
        
        print("\n--- Testing Attraction Query ---")
        result = rag.query_attractions("madinah", "shopping")
        print(f"Answer: {result['answer'][:200]}...")
