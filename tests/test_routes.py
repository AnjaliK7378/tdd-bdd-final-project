# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Product API Service Test Suite
"""
import os
import logging
import unittest
from decimal import Decimal
from service import app
from service.models import db, Product, init_db, Category
from service.common import status
from tests.factories import ProductFactory

# Disable all but critical errors during test run
logging.disable(logging.CRITICAL)

# Define the base URL for the products
BASE_URL = "/products"

######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(unittest.TestCase):
    """Product Route Test Cases"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_products(self, count):
        """Creates an array of Products in the database"""
        products = []
        for _ in range(count):
            product = ProductFactory()
            response = self.client.post(BASE_URL, json=product.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Product",
            )
            new_product = response.get_json()
            product.id = new_product["id"]
            products.append(product)
        return products

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Corrected assertion string to match the page content
        self.assertIn(b"Product Catalog Administration", response.get_data())

    def test_create_product(self):
        """It should Create a new Product"""
        product = ProductFactory()
        response = self.client.post(
            BASE_URL, json=product.serialize(), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check location header
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)
        
        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], product.name, "Name does not match")
        self.assertEqual(new_product["description"], product.description, "Description does not match")
        self.assertEqual(Decimal(new_product["price"]), product.price, "Price does not match")
        self.assertEqual(new_product["available"], product.available, "Available does not match")
        self.assertEqual(new_product["category"], product.category.name, "Category does not match")

    def test_get_product(self):
        """It should Read a single Product"""
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)
        self.assertEqual(data["description"], test_product.description)
        self.assertEqual(Decimal(data["price"]), test_product.price)
        self.assertEqual(data["available"], test_product.available)
        self.assertEqual(data["category"], test_product.category.name)

    def test_get_product_not_found(self):
        """It should not Read a Product that is not found"""
        response = self.client.get(f"{BASE_URL}/0") # Use a known missing ID
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """It should Update an existing Product"""
        test_product = self._create_products(1)[0]
        original_id = test_product.id
        
        # Update the product's description
        new_description = "A brand new, updated description"
        test_product.description = new_description
        
        # Make the PUT request
        response = self.client.put(f"{BASE_URL}/{test_product.id}", json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Fetch the product back to ensure the change was saved
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.get_json()
        self.assertEqual(data["id"], original_id)
        self.assertEqual(data["description"], new_description)

    def test_delete_product(self):
        """It should Delete a Product"""
        test_product = self._create_products(1)[0]
        self.assertEqual(len(Product.all()), 1)
        
        # Send the DELETE request
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check that the product is now gone
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should List all Products"""
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)
    
    def test_list_by_name(self):
        """It should List Products by Name"""
        products = self._create_products(5)
        name_to_find = products[0].name
        count = len([p for p in products if p.name == name_to_find])
        
        response = self.client.get(BASE_URL, query_string=f"name={name_to_find}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), count)
        for product in data:
            self.assertEqual(product["name"], name_to_find)

    def test_list_by_category(self):
        """It should List Products by Category"""
        self._create_products(5) # Create some random products
        
        # Create a product with a specific category for testing
        test_category = Category.TOOLS
        product = ProductFactory(category=test_category)
        
        # Use the raw POST to avoid using the helper which assumes all products created pass
        response = self.client.post(BASE_URL, json=product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(BASE_URL, query_string=f"category={test_category.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # The result must contain at least the one product we manually created
        data = response.get_json()
        self.assertGreaterEqual(len(data), 1) 
        
        for product in data:
            self.assertEqual(product["category"], test_category.name)

    def test_list_by_availability(self):
        """It should List Products by Availability"""
        self._create_products(10)
        
        # Find out how many are available=True
        available_count = len([p for p in Product.all() if p.available is True])
        
        response = self.client.get(BASE_URL, query_string="available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), available_count)
        
        for product in data:
            self.assertEqual(product["available"], True)
