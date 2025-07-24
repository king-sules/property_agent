import pandas as pd
from google.cloud import firestore
import os

# --- Configuration ---
EXCEL_FILE_PATH = 'Properties Listing.xlsx'
# Ensure your service account key has Firestore permissions
# Set the environment variable before running:
# export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service_account_key.json"

def upload_properties_to_firestore():
    """
    A one-time script to read property data from an Excel file
    and upload it to a 'properties' collection in Firestore.
    """
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "firebase_key.json"
        # Initialize Firestore Client
        db = firestore.Client()
        print("Successfully connected to Firestore.")

        # Read the Excel file
        df = pd.read_excel(EXCEL_FILE_PATH)
        print(f"Reading data from '{EXCEL_FILE_PATH}'...")

        # Get a reference to the 'properties' collection
        properties_collection = db.collection('properties')

        # Iterate over each row in the DataFrame and upload it
        for index, row in df.iterrows():
            # Convert row to a dictionary
            property_data = row.to_dict()
            
            # Use a specific ID if you have one, or let Firestore auto-generate
            # For simplicity, we'll use the property name or let it be auto-ID'd
            # Let's use the index as a document ID for now
            doc_id = str(index)
            
            properties_collection.document(doc_id).set(property_data)
            print(f"  - Uploaded property with ID: {doc_id}")

        print("\nAll properties have been successfully uploaded to Firestore!")

    except FileNotFoundError:
        print(f"ERROR: The file '{EXCEL_FILE_PATH}' was not found.")
        print("Please make sure the Excel file is in the same directory as this script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please ensure your GCP authentication is set up correctly.")

if __name__ == "__main__":
    # Important: Make sure you've set up your GCP credentials.
    # The simplest way is to run `gcloud auth application-default login`
    # or set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print("WARNING: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        print("The script might fail if default credentials are not configured.")
    
    upload_properties_to_firestore() 