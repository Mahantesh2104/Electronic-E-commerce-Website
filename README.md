# Electronic Shop

A simple electronic e-commerce website built with Flask and MongoDB for local use.

## Prerequisites

- Python 3.8 or higher
- MongoDB installed and running locally
- pip (Python package installer)

## Setup Instructions

1. Install MongoDB
   - Download and install MongoDB from [MongoDB Download Center](https://www.mongodb.com/try/download/community)
   - Make sure MongoDB service is running on your machine

2. Create Python Virtual Environment (Optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install Dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Run the Application
   ```bash
   python app.py
   ```

5. Access the Website
   - Open your web browser and go to: http://localhost:5000

## Features

- User registration and login
- Product listing
- Shopping cart functionality
- Basic checkout process

## Database Structure

The application uses MongoDB with the following collections:
- users: Stores user information
- products: Stores product information
- cart: Stores shopping cart items

## Note

This is a basic implementation for local use only. Do not use in production without proper security measures. 