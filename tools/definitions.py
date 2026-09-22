from google.genai import types

Schema = types.Schema
Type = types.Type


SEARCH_CATALOG = types.FunctionDeclaration(
    name="search_catalog",
    description=(
        "Search the merchant's product catalog. Call this when the user asks about products, "
        "wants to find something, or says 'show me X'. Returns a list of matching products "
        "with IDs, names, descriptions, and prices in minor units (cents)."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "query": Schema(type=Type.STRING, description="Free-text search term matched against product name and description"),
            "filters": Schema(
                type=Type.OBJECT,
                properties={
                    "categories": Schema(type=Type.ARRAY, items=Schema(type=Type.STRING), description="Filter by category names"),
                    "price": Schema(
                        type=Type.OBJECT,
                        properties={
                            "min": Schema(type=Type.INTEGER, description="Minimum price in minor units (cents). $10.00 = 1000"),
                            "max": Schema(type=Type.INTEGER, description="Maximum price in minor units (cents). $150.00 = 15000"),
                        },
                    ),
                },
            ),
            "pagination": Schema(
                type=Type.OBJECT,
                properties={
                    "limit": Schema(type=Type.INTEGER, description="Number of results to return (default 10)"),
                    "cursor": Schema(type=Type.STRING, description="Cursor from previous response for next page"),
                },
            ),
        },
        required=["query"],
    ),
)

CREATE_CART = types.FunctionDeclaration(
    name="create_cart",
    description=(
        "Create a new shopping cart, optionally with initial items. "
        "Returns a cart ID. Call this before adding items."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "line_items": Schema(
                type=Type.ARRAY,
                items=Schema(
                    type=Type.OBJECT,
                    properties={
                        "product_id": Schema(type=Type.STRING, description="Product ID from search_catalog"),
                        "quantity": Schema(type=Type.INTEGER, description="Number of units"),
                    },
                    required=["product_id", "quantity"],
                ),
                description="Optional initial items to add to the cart",
            ),
        },
    ),
)

GET_CART = types.FunctionDeclaration(
    name="get_cart",
    description="Retrieve the current contents and total of a cart.",
    parameters=Schema(
        type=Type.OBJECT,
        properties={"id": Schema(type=Type.STRING, description="Cart ID returned by create_cart")},
        required=["id"],
    ),
)

UPDATE_CART = types.FunctionDeclaration(
    name="update_cart",
    description=(
        "Update item quantities in the cart. Set quantity to 0 to remove an item. "
        "Items not in line_items are unchanged."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "id": Schema(type=Type.STRING, description="Cart ID returned by create_cart"),
            "line_items": Schema(
                type=Type.ARRAY,
                items=Schema(
                    type=Type.OBJECT,
                    properties={
                        "product_id": Schema(type=Type.STRING, description="Product ID to update"),
                        "quantity": Schema(type=Type.INTEGER, description="New quantity (0 to remove)"),
                    },
                    required=["product_id", "quantity"],
                ),
                description="Items to update",
            ),
        },
        required=["id", "line_items"],
    ),
)

CREATE_CHECKOUT = types.FunctionDeclaration(
    name="create_checkout",
    description=(
        "Create a checkout session from the cart. Returns a checkout ID. "
        "Optionally include buyer email and shipping address to pre-populate."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "checkout": Schema(
                type=Type.OBJECT,
                properties={
                    "cart_id": Schema(type=Type.STRING, description="Cart ID from create_cart"),
                    "buyer": Schema(
                        type=Type.OBJECT,
                        properties={
                            "email": Schema(type=Type.STRING, description="Buyer email address"),
                            "first_name": Schema(type=Type.STRING),
                            "last_name": Schema(type=Type.STRING),
                        },
                    ),
                    "shipping_address": Schema(
                        type=Type.OBJECT,
                        properties={
                            "line1": Schema(type=Type.STRING, description="Street address line 1"),
                            "line2": Schema(type=Type.STRING, description="Apt, suite, etc. (optional)"),
                            "city": Schema(type=Type.STRING),
                            "state": Schema(type=Type.STRING, description="State or province"),
                            "postal_code": Schema(type=Type.STRING),
                            "country": Schema(type=Type.STRING, description="ISO 3166-1 alpha-2 country code, e.g. US"),
                        },
                        required=["line1", "city", "state", "postal_code", "country"],
                    ),
                },
                required=["cart_id"],
            ),
        },
        required=["checkout"],
    ),
)

UPDATE_CHECKOUT = types.FunctionDeclaration(
    name="update_checkout",
    description=(
        "Update buyer info and/or shipping address on a checkout. "
        "When both buyer.email and a complete shipping_address are present, "
        "status becomes ready_for_complete and payment can be requested."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "id": Schema(type=Type.STRING, description="Checkout ID from create_checkout"),
            "checkout": Schema(
                type=Type.OBJECT,
                properties={
                    "buyer": Schema(
                        type=Type.OBJECT,
                        properties={
                            "email": Schema(type=Type.STRING, description="Buyer email address"),
                            "first_name": Schema(type=Type.STRING),
                            "last_name": Schema(type=Type.STRING),
                        },
                    ),
                    "shipping_address": Schema(
                        type=Type.OBJECT,
                        properties={
                            "line1": Schema(type=Type.STRING),
                            "line2": Schema(type=Type.STRING),
                            "city": Schema(type=Type.STRING),
                            "state": Schema(type=Type.STRING),
                            "postal_code": Schema(type=Type.STRING),
                            "country": Schema(type=Type.STRING),
                        },
                        required=["line1", "city", "state", "postal_code", "country"],
                    ),
                },
            ),
        },
        required=["id"],
    ),
)

COMPLETE_CHECKOUT = types.FunctionDeclaration(
    name="complete_checkout",
    description=(
        "Complete the checkout and place the order. "
        "Only call this AFTER request_payment has been shown and the user has confirmed payment. "
        "The checkout must be in ready_for_complete status. Returns status=completed with order."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={"id": Schema(type=Type.STRING, description="Checkout ID from create_checkout")},
        required=["id"],
    ),
)

GET_ORDER = types.FunctionDeclaration(
    name="get_order",
    description="Retrieve a placed order by ID. Returns order details including line items and totals in minor units (cents).",
    parameters=Schema(
        type=Type.OBJECT,
        properties={"id": Schema(type=Type.STRING, description="Order ID from complete_checkout response")},
        required=["id"],
    ),
)

REQUEST_PAYMENT_TOOL = types.FunctionDeclaration(
    name="request_payment",
    description=(
        "Signal that the checkout is ready for payment. Call this when checkout status is "
        "'ready_for_complete'. This triggers the payment UI in the browser. "
        "Do NOT call complete_checkout yourself — the payment system handles that."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "total_minor_units": Schema(type=Type.INTEGER, description="Total amount in minor units (cents)"),
            "currency": Schema(type=Type.STRING, description="ISO 4217 currency code, e.g. USD"),
            "checkout_id": Schema(type=Type.STRING, description="The checkout ID to complete after payment"),
        },
        required=["total_minor_units", "currency", "checkout_id"],
    ),
)

REQUEST_PAYMENT = REQUEST_PAYMENT_TOOL

UCP_TOOLS = [
    SEARCH_CATALOG,
    CREATE_CART,
    GET_CART,
    UPDATE_CART,
    CREATE_CHECKOUT,
    UPDATE_CHECKOUT,
    COMPLETE_CHECKOUT,
    GET_ORDER,
    REQUEST_PAYMENT,
]
