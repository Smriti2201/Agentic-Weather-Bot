#!/usr/bin/env python3
"""
Cornell Store Database Setup

Creates a sample SQLite database with Products and Sales tables for the SQL Agent.
Designed to demonstrate Cornell-level database design principles.

Author: [Your Name]
Date: March 2026
"""

import sqlite3
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random


class CornellStoreDatabase:
    """
    Database builder for Cornell Store e-commerce system.
    
    Attributes:
        db_path: Path to the SQLite database file
    """
    
    def __init__(self, db_path: str = "cornell_store.db") -> None:
        """
        Initialize the database builder.
        
        Args:
            db_path: Path where to create the database
        """
        self.db_path = db_path
    
    def create_tables(self) -> None:
        """Create Products and Sales tables with proper constraints."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create Products table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sku TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
                        stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
                        supplier TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create Sales table with foreign key
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sales (
                        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        quantity_sold INTEGER NOT NULL CHECK (quantity_sold > 0),
                        unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
                        total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),
                        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        customer_email TEXT,
                        FOREIGN KEY (product_id) REFERENCES products(product_id)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id)")
                
                conn.commit()
                print("✅ Tables created successfully")
        
        except sqlite3.Error as e:
            print(f"❌ Error creating tables: {e}")
            raise
    
    def generate_sample_products(self) -> List[Dict[str, Any]]:
        """Generate realistic Cornell Store product data."""
        products = [
            {
                "sku": "CORNELL-HOODIE-001",
                "name": "Cornell Big Red Hoodie",
                "category": "Apparel",
                "price": 65.99,
                "stock_quantity": 45,
                "supplier": "Campus Gear Co."
            },
            {
                "sku": "CORNELL-MUG-002",
                "name": "Cornell Engineering Mug",
                "category": "Accessories",
                "price": 14.99,
                "stock_quantity": 120,
                "supplier": "University Supplies"
            },
            {
                "sku": "CORNELL-NOTEBOOK-003",
                "name": "Cornell Lab Notebook",
                "category": "Stationery",
                "price": 8.50,
                "stock_quantity": 200,
                "supplier": "Academic Press"
            },
            {
                "sku": "CORNELL-TSHIRT-004",
                "name": "Cornell Athletics T-Shirt",
                "category": "Apparel",
                "price": 29.99,
                "stock_quantity": 75,
                "supplier": "Sports Apparel Inc."
            },
            {
                "sku": "CORNELL-BACKPACK-005",
                "name": "Cornell Canvas Backpack",
                "category": "Accessories",
                "price": 89.99,
                "stock_quantity": 30,
                "supplier": "Campus Gear Co."
            },
            {
                "sku": "CORNELL-PEN-006",
                "name": "Cornell Fountain Pen Set",
                "category": "Stationery",
                "price": 45.00,
                "stock_quantity": 60,
                "supplier": "Premium Writing Co."
            },
            {
                "sku": "CORNELL-SWEATPANTS-007",
                "name": "Cornell Big Red Sweatpants",
                "category": "Apparel",
                "price": 49.99,
                "stock_quantity": 55,
                "supplier": "Campus Gear Co."
            },
            {
                "sku": "CORNELL-WATERBOTTLE-008",
                "name": "Cornell Insulated Water Bottle",
                "category": "Accessories",
                "price": 24.99,
                "stock_quantity": 90,
                "supplier": "Eco Products Ltd."
            },
            {
                "sku": "CORNELL-PLANNER-009",
                "name": "Cornell 2024-25 Planner",
                "category": "Stationery",
                "price": 18.99,
                "stock_quantity": 150,
                "supplier": "Academic Press"
            },
            {
                "sku": "CORNELL-HAT-010",
                "name": "Cornell Baseball Cap",
                "category": "Apparel",
                "price": 22.50,
                "stock_quantity": 85,
                "supplier": "Sports Apparel Inc."
            }
        ]
        return products
    
    def generate_sample_sales(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """Generate realistic sales data for the products."""
        sales = []
        customers = [
            "student1@cornell.edu",
            "student2@cornell.edu", 
            "faculty@cornell.edu",
            "staff@cornell.edu",
            "alumni@cornell.edu"
        ]
        
        for i in range(25):  # Generate 25 sales records
            product_id = random.choice(product_ids)
            quantity = random.randint(1, 5)
            
            # Get product price (we'll update this after inserting products)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT price FROM products WHERE product_id = ?", (product_id,))
                result = cursor.fetchone()
                unit_price = result[0] if result else 29.99
            
            total_amount = quantity * unit_price
            
            # Generate random date within last 30 days
            days_ago = random.randint(0, 30)
            sale_date = datetime.now() - timedelta(days=days_ago)
            
            sales.append({
                "product_id": product_id,
                "quantity_sold": quantity,
                "unit_price": unit_price,
                "total_amount": total_amount,
                "sale_date": sale_date.strftime("%Y-%m-%d %H:%M:%S"),
                "customer_email": random.choice(customers) if random.random() > 0.3 else None
            })
        
        return sales
    
    def populate_database(self) -> None:
        """Populate the database with sample data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert products
                products = self.generate_sample_products()
                product_ids = []
                
                for product in products:
                    cursor.execute("""
                        INSERT INTO products (sku, name, category, price, stock_quantity, supplier)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        product["sku"],
                        product["name"], 
                        product["category"],
                        product["price"],
                        product["stock_quantity"],
                        product["supplier"]
                    ))
                    product_ids.append(cursor.lastrowid)
                
                print(f"✅ Inserted {len(products)} products")
                
                # Insert sales
                sales = self.generate_sample_sales(product_ids)
                for sale in sales:
                    cursor.execute("""
                        INSERT INTO sales (product_id, quantity_sold, unit_price, total_amount, sale_date, customer_email)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        sale["product_id"],
                        sale["quantity_sold"],
                        sale["unit_price"],
                        sale["total_amount"],
                        sale["sale_date"],
                        sale["customer_email"]
                    ))
                
                print(f"✅ Inserted {len(sales)} sales records")
                
                conn.commit()
        
        except sqlite3.Error as e:
            print(f"❌ Error populating database: {e}")
            raise
    
    def get_database_info(self) -> None:
        """Display database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Product statistics
                cursor.execute("SELECT COUNT(*) FROM products")
                product_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sales")
                sales_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(total_amount) FROM sales")
                total_revenue = cursor.fetchone()[0] or 0
                
                print(f"\n📊 Database Statistics:")
                print(f"   Products: {product_count}")
                print(f"   Sales: {sales_count}")
                print(f"   Total Revenue: ${total_revenue:.2f}")
                
                # Show sample data
                print(f"\n🛍️  Sample Products:")
                cursor.execute("SELECT name, category, price FROM products LIMIT 3")
                for row in cursor.fetchall():
                    print(f"   {row[0]} ({row[1]}) - ${row[2]}")
                
                print(f"\n💰 Recent Sales:")
                cursor.execute("""
                    SELECT p.name, s.quantity_sold, s.total_amount, s.sale_date 
                    FROM sales s 
                    JOIN products p ON s.product_id = p.product_id 
                    ORDER BY s.sale_date DESC 
                    LIMIT 3
                """)
                for row in cursor.fetchall():
                    print(f"   {row[0]} - {row[1]} units - ${row[2]} ({row[3]})")
        
        except sqlite3.Error as e:
            print(f"❌ Error getting database info: {e}")
    
    def build_database(self) -> None:
        """Complete database building process."""
        print(f"🏗️  Building Cornell Store database: {self.db_path}")
        
        # Remove existing database if it exists
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"🗑️  Removed existing database")
        
        # Create and populate
        self.create_tables()
        self.populate_database()
        self.get_database_info()
        
        print(f"\n✅ Cornell Store database built successfully!")
        print(f"📍 Location: {os.path.abspath(self.db_path)}")


def main() -> None:
    """Main function to run the database setup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Cornell Store database")
    parser.add_argument(
        "--db-path",
        help="Path for the database file",
        default="cornell_store.db"
    )
    
    args = parser.parse_args()
    
    try:
        builder = CornellStoreDatabase(args.db_path)
        builder.build_database()
    
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
