import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
import math
import json
import re
from typing import Optional, Dict, List, Union

# Initialize session state and directories
st.set_page_config(
    page_title="AgriculturalHub - Buy & Sell Agricultural Products",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state variables
if 'current_view' not in st.session_state:
    st.session_state.current_view = "main"
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'my_transport_listings' not in st.session_state:
    st.session_state.my_transport_listings = []

# Create necessary directories
os.makedirs('data', exist_ok=True)
os.makedirs('images/uploads', exist_ok=True)

# Database connection with connection pooling
class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        self.conn = sqlite3.connect('agrimarket.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.initialize_tables()
    
    def initialize_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS crop_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            seller_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            location TEXT NOT NULL,
            image_path TEXT,
            date TEXT NOT NULL,
            CHECK (quantity > 0),
            CHECK (price > 0)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pesticide_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pesticide_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            price REAL NOT NULL,
            seller_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            location TEXT NOT NULL,
            image_path TEXT,
            date TEXT NOT NULL,
            CHECK (quantity > 0),
            CHECK (price > 0)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transport_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_type TEXT NOT NULL,
            capacity REAL NOT NULL,
            capacity_unit TEXT NOT NULL,
            rate_per_km REAL NOT NULL,
            available_from TEXT NOT NULL,
            available_to TEXT,
            available_date TEXT,
            provider_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            description TEXT,
            is_available INTEGER NOT NULL DEFAULT 1,
            image_path TEXT,
            date TEXT NOT NULL,
            CHECK (capacity > 0),
            CHECK (rate_per_km > 0)
        )
        ''')
        
        self.conn.commit()
    
    def get_connection(self):
        return self.conn
    
    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()

# Initialize database singleton
db = Database()

# Utility functions
def validate_phone_number(phone: str) -> bool:
    """Validate Indian phone numbers"""
    pattern = re.compile(r'^(\+91[\-\s]?)?[0]?(91)?[6789]\d{9}$')
    return bool(pattern.match(phone))

def validate_input(text: str, field_name: str, min_length: int = 2) -> bool:
    """Validate text input"""
    if not text or len(text.strip()) < min_length:
        st.error(f"{field_name} must be at least {min_length} characters long")
        return False
    return True

def save_uploaded_image(uploaded_file) -> Optional[str]:
    """Save uploaded image and return the file path"""
    if uploaded_file is None:
        return None
    
    try:
        # Validate file type
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in ['.jpg', '.jpeg', '.png']:
            st.error("Only JPG/JPEG/PNG images are allowed")
            return None
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"product_{timestamp}{file_extension}"
        filepath = os.path.join("images/uploads", filename)
        
        # Process and save image
        img = Image.open(uploaded_file)
        
        # Resize if too large
        if img.size[0] > 1024 or img.size[1] > 1024:
            img.thumbnail((1024, 1024))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img.save(filepath, quality=85)
        return filepath
    
    except Exception as e:
        st.error(f"Failed to save image: {str(e)}")
        return None

def get_image_as_base64(path: str) -> Optional[str]:
    """Convert an image to base64 for embedded display"""
    if not path or not os.path.exists(path):
        return None
    
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return None

# Database operations
def save_crop_listing(listing_data: Dict) -> bool:
    """Save a crop listing to the database"""
    if not all(key in listing_data for key in ['crop_name', 'quantity', 'price', 'seller_name', 'contact', 'location', 'date']):
        st.error("Missing required fields in crop listing data")
        return False
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO crop_listings 
        (crop_name, quantity, price, seller_name, contact, location, image_path, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_data['crop_name'],
            float(listing_data['quantity']),
            float(listing_data['price']),
            listing_data['seller_name'],
            listing_data['contact'],
            listing_data['location'],
            listing_data.get('image_path'),
            listing_data['date']
        ))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error saving crop listing: {e}")
        return False
    except ValueError as e:
        st.error(f"Invalid number format: {e}")
        return False

def save_pesticide_listing(listing_data: Dict) -> bool:
    """Save a pesticide listing to the database"""
    if not all(key in listing_data for key in ['pesticide_name', 'quantity', 'unit', 'price', 'seller_name', 'contact', 'location', 'date']):
        st.error("Missing required fields in pesticide listing data")
        return False
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO pesticide_listings 
        (pesticide_name, quantity, unit, price, seller_name, contact, location, image_path, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_data['pesticide_name'],
            float(listing_data['quantity']),
            listing_data['unit'],
            float(listing_data['price']),
            listing_data['seller_name'],
            listing_data['contact'],
            listing_data['location'],
            listing_data.get('image_path'),
            listing_data['date']
        ))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error saving pesticide listing: {e}")
        return False
    except ValueError as e:
        st.error(f"Invalid number format: {e}")
        return False

def get_all_crop_listings() -> List[Dict]:
    """Get all crop listings from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crop_listings ORDER BY date DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Database error getting crop listings: {e}")
        return []

def get_all_pesticide_listings() -> List[Dict]:
    """Get all pesticide listings from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pesticide_listings ORDER BY date DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Database error getting pesticide listings: {e}")
        return []

def delete_crop_listing(listing_id: int) -> bool:
    """Delete a crop listing from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crop_listings WHERE id = ?", (listing_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Database error deleting crop listing: {e}")
        return False

def delete_pesticide_listing(listing_id: int) -> bool:
    """Delete a pesticide listing from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pesticide_listings WHERE id = ?", (listing_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Database error deleting pesticide listing: {e}")
        return False

def save_transport_listing(listing_data: Dict) -> bool:
    """Save a transport listing to the database"""
    required_fields = ['vehicle_type', 'capacity', 'capacity_unit', 'rate_per_km', 
                      'available_from', 'provider_name', 'contact', 'date']
    
    if not all(key in listing_data for key in required_fields):
        st.error("Missing required fields in transport listing data")
        return False
    
    try:
        available_date = None
        if 'available_date' in listing_data and listing_data['available_date']:
            if isinstance(listing_data['available_date'], str):
                available_date = listing_data['available_date']
            else:
                available_date = listing_data['available_date'].strftime("%Y-%m-%d")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO transport_listings 
        (vehicle_type, capacity, capacity_unit, rate_per_km, available_from, available_to,
         available_date, provider_name, contact, description, is_available, image_path, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_data['vehicle_type'],
            float(listing_data['capacity']),
            listing_data['capacity_unit'],
            float(listing_data['rate_per_km']),
            listing_data['available_from'],
            listing_data.get('available_to'),
            available_date,
            listing_data['provider_name'],
            listing_data['contact'],
            listing_data.get('description'),
            1,  # is_available = True
            listing_data.get('image_path'),
            listing_data['date']
        ))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error saving transport listing: {e}")
        return False
    except ValueError as e:
        st.error(f"Invalid number format: {e}")
        return False

def get_all_transport_listings() -> List[Dict]:
    """Get all transport listings from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transport_listings ORDER BY date DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Database error getting transport listings: {e}")
        return []

def get_available_transport_listings() -> List[Dict]:
    """Get only available transport listings from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transport_listings WHERE is_available = 1 ORDER BY date DESC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        st.error(f"Database error getting available transport listings: {e}")
        return []

def update_transport_availability(listing_id: int, is_available: bool) -> bool:
    """Update the availability status of a transport listing"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transport_listings SET is_available = ? WHERE id = ?",
            (1 if is_available else 0, listing_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Database error updating transport availability: {e}")
        return False

def delete_transport_listing(listing_id: int) -> bool:
    """Delete a transport listing from the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transport_listings WHERE id = ?", (listing_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        st.error(f"Database error deleting transport listing: {e}")
        return False

# UI Components
def show_header():
    st.markdown("""
    <div style="background: linear-gradient(to right, #0E1117, #262730); padding: 20px; border-radius: 15px; 
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); margin-bottom: 30px; display: flex; align-items: center;">
        <img src="https://img.freepik.com/free-vector/farmland-logo-design-template_23-2149511359.jpg" 
             style="width:100px; height:100px; border-radius: 50%; margin-right: 20px; border: 2px solid #4CAF50;"
             alt="AgriMarket Logo">
        <div>
            <h1 style="margin: 0; color: #5CDB95; font-size: 2.5rem; font-weight: 800;">AgriMarket</h1>
            <h3 style="margin: 0; color: #ffffff; font-weight: 400; opacity: 0.8;">Buy & Sell Agricultural Products</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_main_page():
    show_header()
    
    st.markdown("### Welcome to AgriMarket")
    st.markdown("""
    Connect with farmers and agricultural suppliers in your area.
    Buy or sell crops, pesticides, and other agricultural products.
    Now with transport services to move your agricultural goods!
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.image("https://img.freepik.com/free-photo/woman-holding-basket-full-vegetables_23-2149182044.jpg", 
                width=200, caption="Buy Fresh Produce")
        if st.button("Buy Products", use_container_width=True):
            st.session_state.current_view = "buy"
            st.rerun()
    
    with col2:
        st.image("https://img.freepik.com/free-photo/farmer-holds-orange-pumpkin-wooden-box-with-vegetables-harvest-eco-farm-autumn-harvest-vegetables_1150-45620.jpg", 
                width=200, caption="Sell Your Harvest")
        if st.button("Sell Products", use_container_width=True):
            st.session_state.current_view = "sell"
            st.rerun()
    
    with col3:
        st.image("https://img.freepik.com/free-photo/delivery-concept-handsome-african-american-delivery-man-isolated-grey-studio-background_1157-48472.jpg", 
                width=200, caption="Transport Services")
        if st.button("Transport Services", use_container_width=True):
            st.session_state.current_view = "transport"
            st.rerun()
    
    st.markdown("### Recent Listings")
    
    crop_listings = get_all_crop_listings()
    pesticide_listings = get_all_pesticide_listings()
    
    if not crop_listings and not pesticide_listings:
        st.info("No listings available yet. Be the first to add a listing!")
    else:
        tabs = st.tabs(["Crops", "Pesticides"])
        
        with tabs[0]:
            if crop_listings:
                show_crop_listings(crop_listings[:5])  # Show only 5 most recent listings
            else:
                st.info("No crop listings available yet.")
        
        with tabs[1]:
            if pesticide_listings:
                show_pesticide_listings(pesticide_listings[:5])  # Show only 5 most recent listings
            else:
                st.info("No pesticide listings available yet.")

def show_crop_listings(listings: List[Dict]):
    for i, listing in enumerate(listings):
        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(to bottom right, #1E2530, #2E3440); 
                        border-radius: 15px; padding: 1rem; margin-bottom: 1.5rem;
                        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.3); border: 1px solid rgba(76, 175, 80, 0.2);">
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if 'image_path' in listing and listing['image_path'] and os.path.exists(listing['image_path']):
                    st.image(listing['image_path'], width=200, caption=listing['crop_name'])
                else:
                    st.image("https://img.freepik.com/free-photo/plant-growing-soil-with-word-organic_1150-18226.jpg", 
                            width=200, caption="Product Image")
            
            with col2:
                st.subheader(listing['crop_name'])
                
                st.markdown(
                    f"""
                    <div style="background-color: rgba(76, 175, 80, 0.2); display: inline-block; 
                              padding: 5px 10px; border-radius: 15px; margin-bottom: 10px;
                              border: 1px solid #4CAF50; color: #5CDB95; font-weight: bold;">
                        Crop
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.markdown(f"**Quantity:** {listing['quantity']} kg")
                with col_b:
                    st.markdown(f"**Price:** ₹{listing['price']} per kg")
                with col_c:
                    total_value = float(listing['quantity']) * float(listing['price'])
                    st.markdown(
                        f"""
                        <div style="background-color: rgba(76, 175, 80, 0.15); padding: 8px; 
                                  border-radius: 5px; text-align: center; font-weight: bold;">
                            Total: ₹{total_value:.2f}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                st.markdown(f"**Location:** {listing['location']}")
                st.markdown(f"**Seller:** {listing['seller_name']}")
                st.markdown(f"**Contact:** {listing['contact']}")
                st.markdown(f"**Listed on:** {listing.get('date', 'N/A')}")
                
                st.button(f"Contact Seller 📞", key=f"contact_{i}")
        
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

def show_pesticide_listings(listings: List[Dict]):
    for i, listing in enumerate(listings):
        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(to bottom right, #1E2530, #2E3440); 
                        border-radius: 15px; padding: 1rem; margin-bottom: 1.5rem;
                        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.3); border: 1px solid rgba(76, 175, 80, 0.2);">
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if 'image_path' in listing and listing['image_path'] and os.path.exists(listing['image_path']):
                    st.image(listing['image_path'], width=200, caption=listing['pesticide_name'])
                else:
                    st.image("https://img.freepik.com/free-photo/farmer-spraying-pesticide-crops_23-2148488637.jpg", 
                            width=200, caption="Pesticide Image")
            
            with col2:
                st.subheader(listing['pesticide_name'])
                
                st.markdown(
                    f"""
                    <div style="background-color: rgba(76, 175, 80, 0.2); display: inline-block; 
                              padding: 5px 10px; border-radius: 15px; margin-bottom: 10px;
                              border: 1px solid #4CAF50; color: #5CDB95; font-weight: bold;">
                        Pesticide
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.markdown(f"**Quantity:** {listing['quantity']} {listing['unit']}")
                with col_b:
                    st.markdown(f"**Price:** ₹{listing['price']} per {listing['unit']}")
                with col_c:
                    total_value = float(listing['quantity']) * float(listing['price'])
                    st.markdown(
                        f"""
                        <div style="background-color: rgba(76, 175, 80, 0.15); padding: 8px; 
                                  border-radius: 5px; text-align: center; font-weight: bold;">
                            Total: ₹{total_value:.2f}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                
                st.markdown(f"**Location:** {listing['location']}")
                st.markdown(f"**Seller:** {listing['seller_name']}")
                st.markdown(f"**Contact:** {listing['contact']}")
                st.markdown(f"**Listed on:** {listing.get('date', 'N/A')}")
                
                st.button(f"Contact Seller 📞", key=f"pesticide_contact_{i}")
        
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)

def show_buy_page():
    show_header()
    
    st.markdown("### Buy Agricultural Products")
    
    if st.button("← Back to Main Page"):
        st.session_state.current_view = "main"
        st.rerun()
    
    product_type = st.radio("Select Product Type", ["Crops", "Pesticides"], horizontal=True)
    
    if product_type == "Crops":
        crop_listings = get_all_crop_listings()
        if not crop_listings:
            st.info("No crop listings available. Check back later or add your own listing!")
        else:
            show_crop_listings(crop_listings)
    else:
        pesticide_listings = get_all_pesticide_listings()
        if not pesticide_listings:
            st.info("No pesticide listings available. Check back later or add your own listing!")
        else:
            show_pesticide_listings(pesticide_listings)

def show_sell_page():
    show_header()
    
    st.markdown("### Sell Agricultural Products")
    
    if st.button("← Back to Main Page"):
        st.session_state.current_view = "main"
        st.rerun()
    
    product_type = st.radio("What are you selling?", ["Crops", "Pesticides"], horizontal=True)
    
    if product_type == "Crops":
        show_crop_sell_form()
    else:
        show_pesticide_sell_form()

def show_crop_sell_form():
    st.markdown("### List Your Crops for Sale")
    
    with st.form("crop_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            crop_name = st.text_input("Crop Name*")
            quantity = st.number_input("Quantity (kg)*", min_value=0.1, step=0.5, format="%.1f")
            price = st.number_input("Price per kg (₹)*", min_value=0.1, step=0.5, format="%.2f")
        
        with col2:
            seller_name = st.text_input("Your Name*")
            contact = st.text_input("Contact Number*", placeholder="10-digit mobile number")
            location = st.text_input("Location*", placeholder="City/Village, State")
        
        st.markdown("### Add an Image of Your Product (Optional)")
        uploaded_file = st.file_uploader("Choose an image (JPG/PNG)", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Preview", width=300)
        
        submitted = st.form_submit_button("List Crop for Sale")
        
        if submitted:
            # Validate inputs
            errors = []
            
            if not validate_input(crop_name, "Crop name"):
                errors.append("Invalid crop name")
            
            if not validate_input(seller_name, "Your name"):
                errors.append("Invalid seller name")
            
            if not validate_input(location, "Location"):
                errors.append("Invalid location")
            
            if not validate_phone_number(contact):
                errors.append("Please enter a valid 10-digit Indian phone number")
                st.error("Please enter a valid 10-digit Indian phone number")
            
            if quantity <= 0:
                errors.append("Quantity must be greater than 0")
            
            if price <= 0:
                errors.append("Price must be greater than 0")
            
            if not errors:
                image_path = save_uploaded_image(uploaded_file) if uploaded_file else None
                
                listing = {
                    'crop_name': crop_name.strip(),
                    'quantity': quantity,
                    'price': price,
                    'seller_name': seller_name.strip(),
                    'contact': contact.strip(),
                    'location': location.strip(),
                    'image_path': image_path,
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if save_crop_listing(listing):
                    st.success("Your crop has been listed successfully!")
                    st.balloons()
                else:
                    st.error("Failed to save your listing. Please try again.")
            else:
                for error in errors:
                    st.error(error)

def show_pesticide_sell_form():
    st.markdown("### List Your Pesticides for Sale")
    
    with st.form("pesticide_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            pesticide_name = st.text_input("Pesticide Name*")
            quantity = st.number_input("Quantity*", min_value=0.1, step=0.5, format="%.1f")
            unit = st.selectbox("Unit*", ["Liters", "Kg", "Bottles", "Packets"])
            price = st.number_input("Price per unit (₹)*", min_value=0.1, step=0.5, format="%.2f")
        
        with col2:
            seller_name = st.text_input("Your Name*")
            contact = st.text_input("Contact Number*", placeholder="10-digit mobile number")
            location = st.text_input("Location*", placeholder="City/Village, State")
        
        st.markdown("### Add an Image of Your Product (Optional)")
        uploaded_file = st.file_uploader("Choose an image (JPG/PNG)", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Preview", width=300)
        
        submitted = st.form_submit_button("List Pesticide for Sale")
        
        if submitted:
            # Validate inputs
            errors = []
            
            if not validate_input(pesticide_name, "Pesticide name"):
                errors.append("Invalid pesticide name")
            
            if not validate_input(seller_name, "Your name"):
                errors.append("Invalid seller name")
            
            if not validate_input(location, "Location"):
                errors.append("Invalid location")
            
            if not validate_phone_number(contact):
                errors.append("Please enter a valid 10-digit Indian phone number")
                st.error("Please enter a valid 10-digit Indian phone number")
            
            if quantity <= 0:
                errors.append("Quantity must be greater than 0")
            
            if price <= 0:
                errors.append("Price must be greater than 0")
            
            if not errors:
                image_path = save_uploaded_image(uploaded_file) if uploaded_file else None
                
                listing = {
                    'pesticide_name': pesticide_name.strip(),
                    'quantity': quantity,
                    'unit': unit,
                    'price': price,
                    'seller_name': seller_name.strip(),
                    'contact': contact.strip(),
                    'location': location.strip(),
                    'image_path': image_path,
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if save_pesticide_listing(listing):
                    st.success("Your pesticide has been listed successfully!")
                    st.balloons()
                else:
                    st.error("Failed to save your listing. Please try again.")
            else:
                for error in errors:
                    st.error(error)

def show_transport_page():
    """Display the transport page with options for offering or finding transport"""
    st.markdown("""
    <div style="background: linear-gradient(to right, #0E1117, #262730); padding: 20px; border-radius: 15px; 
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); margin-bottom: 30px; display: flex; align-items: center;">
        <img src="https://img.freepik.com/free-vector/farmland-logo-design-template_23-2149511359.jpg" 
             style="width:100px; height:100px; border-radius: 50%; margin-right: 20px; border: 2px solid #4CAF50;"
             alt="AgriMarket Logo">
        <div>
            <h1 style="margin: 0; color: #5CDB95; font-size: 2.5rem; font-weight: 800;">AgriMarket</h1>
            <h3 style="margin: 0; color: #ffffff; font-weight: 400; opacity: 0.8;">Transport Services</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("← Back to Main Page"):
        st.session_state.current_view = "main"
        st.rerun()
    
    st.markdown("### Agricultural Transport Marketplace")
    st.markdown("""
    Connect with transport providers to move your agricultural products efficiently and affordably.
    Find the right transport service for your crops and pesticides or offer your own transport services.
    """)
    
    option = st.radio(
        "What would you like to do?",
        ["Find Transport", "Offer Transport Services", "View My Transport Listings"],
        horizontal=True
    )
    
    if option == "Find Transport":
        show_find_transport()
    elif option == "Offer Transport Services":
        show_transport_form()
    else:
        show_my_transport_listings()

def show_find_transport():
    """Display available transport options for users to book"""
    st.header("Find Transport Services")
    
    transport_listings = get_available_transport_listings()
    
    if not transport_listings:
        st.info("No transport services are currently available. Check back later or offer your own transport service!")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        vehicle_types = ["All"] + sorted(list(set(listing['vehicle_type'] for listing in transport_listings)))
        selected_vehicle = st.selectbox("Filter by Vehicle Type", vehicle_types)
    
    with col2:
        locations = ["All"] + sorted(list(set(listing['available_from'] for listing in transport_listings)))
        selected_location = st.selectbox("Filter by Starting Location", locations)
    
    filtered_listings = transport_listings
    if selected_vehicle != "All":
        filtered_listings = [listing for listing in filtered_listings if listing['vehicle_type'] == selected_vehicle]
    
    if selected_location != "All":
        filtered_listings = [listing for listing in filtered_listings if listing['available_from'] == selected_location]
    
    st.subheader("Calculate Transport Cost")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_id = st.selectbox(
            "Select a transport provider", 
            [""] + [f"{listing['id']} - {listing['vehicle_type']} - {listing['provider_name']}" 
                   for listing in filtered_listings]
        )
    
    with col2:
        distance = st.number_input("Distance (km)", min_value=1, value=10)
    
    with col3:
        if selected_id:
            listing_id = int(selected_id.split("-")[0].strip())
            selected_listing = next((listing for listing in filtered_listings if listing['id'] == listing_id), None)
            
            if selected_listing:
                cost = selected_listing['rate_per_km'] * distance
                st.metric("Estimated Cost", f"₹{cost:.2f}")
                
                if st.button("Book Transport", key="book_transport"):
                    st.success(f"Your booking request has been sent to {selected_listing['provider_name']}. They will contact you soon on your registered phone number.")
    
    st.subheader("Available Transport Services")
    
    for listing in filtered_listings:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if 'image_path' in listing and listing['image_path'] and os.path.exists(listing['image_path']):
                st.image(listing['image_path'], width=200, caption=listing['vehicle_type'])
            else:
                st.image("https://img.freepik.com/free-photo/delivery-concept-handsome-african-american-delivery-man-isolated-grey-studio-background_1157-48472.jpg", 
                        width=200, caption="Transport Vehicle")
        
        with col2:
            st.subheader(f"{listing['vehicle_type']} - {listing['provider_name']}")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"**Capacity:** {listing['capacity']} {listing['capacity_unit']}")
            with col_b:
                st.markdown(f"**Rate:** ₹{listing['rate_per_km']} per km")
            with col_c:
                if listing['available_date']:
                    st.markdown(f"**Available on:** {listing['available_date']}")
                else:
                    st.markdown("**Available:** Anytime")
            
            st.markdown(f"**Route:** {listing['available_from']} to {listing['available_to'] if listing['available_to'] else 'Any location'}")
            st.markdown(f"**Contact:** {listing['contact']}")
            
            if listing.get('description'):
                with st.expander("View Details"):
                    st.markdown(listing['description'])
            
            sample_distance = 50  # 50 km example
            sample_cost = listing['rate_per_km'] * sample_distance
            st.markdown(f"**Sample cost for {sample_distance}km:** ₹{sample_cost:.2f}")
            
            if st.button(f"Request Booking - {listing['id']}", key=f"req_booking_{listing['id']}"):
    st.success(f"Your booking request has been sent to {listing['provider_name']}. They will contact you soon.")
