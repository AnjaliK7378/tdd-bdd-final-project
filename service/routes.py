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
Product Service REST API
"""
from flask import jsonify, request, url_for, make_response, abort
from service.common import status  # HTTP Status Codes
from service.models import Product, Category, DataValidationError

# Import Flask application from service
from . import app


######################################################################
# H E A L T H   C H E C K
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# G E T   I N D E X
######################################################################
@app.route("/")
def index():
    """Base URL for the Product Service"""
    return app.send_static_file("index.html")


######################################################################
# C R E A T E   A   N E W   P R O D U C T
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based on the data in the body
    that is posted.
    """
    app.logger.info("Processing CREATE request")
    check_content_type("application/json")
    
    try:
        product = Product()
        product.deserialize(request.get_json())
        product.create()
        
        app.logger.info("Product with ID [%s] created.", product.id)
        
        location_url = url_for("get_products", product_id=product.id, _external=True)
        
        return jsonify(product.serialize()), status.HTTP_201_CREATED, {"Location": location_url}
        
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))
    except Exception as error:
        app.logger.error("Error creating product: %s", error)
        abort(status.HTTP_500_INTERNAL_SERVER_ERROR, str(error))


######################################################################
# L I S T   A L L   P R O D U C T S / Q U E R Y
######################################################################
@app.route("/products", methods=["GET"])
def list_products():
    """Returns all of the Products or searches by query parameters"""
    app.logger.info("Processing List or Search request")
    products = []
    
    # Get query parameters
    name = request.args.get("name")
    category = request.args.get("category")
    available = request.args.get("available")

    if name:
        app.logger.info("Finding products by name: %s", name)
        products = Product.find_by_name(name).all()
    elif category:
        app.logger.info("Finding products by category: %s", category)
        try:
            category_value = Category[category.upper()]
            products = Product.find_by_category(category_value).all()
        except KeyError:
            # Handle case where category is invalid
            abort(status.HTTP_400_BAD_REQUEST, f"Invalid category: {category}")
    elif available:
        app.logger.info("Finding products by availability: %s", available)
        # Convert string 'true'/'false' to boolean
        is_available = available.lower() in ("true", "1", "t")
        products = Product.find_by_availability(is_available).all()
    else:
        app.logger.info("Returning all products")
        products = Product.all()

    # Convert the list of Products to a list of dictionaries
    results = [product.serialize() for product in products]
    app.logger.info("Returning %d products", len(results))
    return jsonify(results), status.HTTP_200_OK


######################################################################
# R E T R I E V E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["GET"])
def get_products(product_id):
    """
    Retrieve a single Product
    This endpoint will return a Product based on its id
    """
    app.logger.info("Processing GET request for product id: %s", product_id)
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id '{product_id}' was not found.")
    
    app.logger.info("Returning product: %s", product.name)
    return product.serialize(), status.HTTP_200_OK


######################################################################
# U P D A T E   A N   E X I S T I N G   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_products(product_id):
    """
    Update a Product
    This endpoint will update a Product based on the body that is posted
    """
    app.logger.info("Processing PUT request for product id: %s", product_id)
    check_content_type("application/json")
    
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id '{product_id}' was not found.")
    
    try:
        product.deserialize(request.get_json())
        product.id = product_id  # make sure they cannot change the id
        product.update()
        
        app.logger.info("Product with ID [%s] updated.", product.id)
        return product.serialize(), status.HTTP_200_OK
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))
    except Exception as error:
        app.logger.error("Error updating product: %s", error)
        abort(status.HTTP_500_INTERNAL_SERVER_ERROR, str(error))


######################################################################
# D E L E T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_products(product_id):
    """
    Delete a Product
    This endpoint will delete a Product based on its id
    """
    app.logger.info("Processing DELETE request for id: %s", product_id)
    product = Product.find(product_id)
    if product:
        product.delete()
        
    app.logger.info("Product with ID [%s] deleted (or not found).", product_id)
    # The spec calls for a 204 NO CONTENT even if the product doesn't exist
    return "", status.HTTP_204_NO_CONTENT


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )
