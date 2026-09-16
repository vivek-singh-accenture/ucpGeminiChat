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

CART_CREATE = types.FunctionDeclaration(
    name="cart_create",
    description="Create a new shopping cart. Call this exactly once per conversation before adding any items. Returns a cartId.",
    parameters=Schema(type=Type.OBJECT, properties={}),
)

CART_ADD_ITEM = types.FunctionDeclaration(
    name="cart_add_item",
    description="Add a product to the cart. Requires the cartId from cart_create and the productId from search_catalog.",
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "cartId": Schema(type=Type.STRING, description="Cart ID returned by cart_create"),
            "productId": Schema(type=Type.STRING, description="Product ID from search_catalog results"),
            "quantity": Schema(type=Type.INTEGER, description="Number of units to add (default 1)"),
        },
        required=["cartId", "productId", "quantity"],
    ),
)

CART_GET = types.FunctionDeclaration(
    name="cart_get",
    description="Retrieve the current contents and total of a cart.",
    parameters=Schema(
        type=Type.OBJECT,
        properties={"cartId": Schema(type=Type.STRING, description="Cart ID returned by cart_create")},
        required=["cartId"],
    ),
)

CART_REMOVE_ITEM = types.FunctionDeclaration(
    name="cart_remove_item",
    description="Remove a product line from the cart.",
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "cartId": Schema(type=Type.STRING, description="Cart ID returned by cart_create"),
            "productId": Schema(type=Type.STRING, description="Product ID to remove"),
        },
        required=["cartId", "productId"],
    ),
)

CHECKOUT_CREATE = types.FunctionDeclaration(
    name="checkout_create",
    description="Create a checkout session from the cart. Returns a checkoutId to use in checkout_update and checkout_complete.",
    parameters=Schema(
        type=Type.OBJECT,
        properties={"cartId": Schema(type=Type.STRING, description="Cart ID returned by cart_create")},
        required=["cartId"],
    ),
)

CHECKOUT_UPDATE = types.FunctionDeclaration(
    name="checkout_update",
    description=(
        "Set the buyer's email address and/or shipping address on a checkout. "
        "When BOTH buyerEmail AND shippingAddress are provided, the checkout transitions to "
        "ready_for_complete status. Always collect both before calling this."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "checkoutId": Schema(type=Type.STRING, description="Checkout ID returned by checkout_create"),
            "buyerEmail": Schema(type=Type.STRING, description="Buyer's email address"),
            "shippingAddress": Schema(type=Type.STRING, description="Full shipping address as a single string, e.g. '123 Main St, Springfield, IL 62701'"),
        },
        required=["checkoutId"],
    ),
)

CHECKOUT_COMPLETE = types.FunctionDeclaration(
    name="checkout_complete",
    description=(
        "Complete the checkout and place the order. "
        "Only call this AFTER request_payment has been shown and the user has confirmed payment. "
        "The checkout must be in ready_for_complete status."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={"checkoutId": Schema(type=Type.STRING, description="Checkout ID returned by checkout_create")},
        required=["checkoutId"],
    ),
)

REQUEST_PAYMENT_TOOL = types.FunctionDeclaration(
    name="request_payment",
    description=(
        "Signal that the checkout is ready for payment. Call this when checkout status is "
        "'ready_for_complete'. This triggers the payment UI in the browser. "
        "Do NOT call checkout_complete yourself — the payment system handles that."
    ),
    parameters=Schema(
        type=Type.OBJECT,
        properties={
            "total_minor_units": Schema(type=Type.INTEGER, description="Total amount in minor units (cents)"),
            "currency": Schema(type=Type.STRING, description="ISO 4217 currency code, e.g. USD"),
            "checkout_id": Schema(type=Type.STRING, description="The checkoutId to complete after payment"),
        },
        required=["total_minor_units", "currency", "checkout_id"],
    ),
)

REQUEST_PAYMENT = REQUEST_PAYMENT_TOOL

UCP_TOOLS = [
    SEARCH_CATALOG,
    CART_CREATE,
    CART_ADD_ITEM,
    CART_GET,
    CART_REMOVE_ITEM,
    CHECKOUT_CREATE,
    CHECKOUT_UPDATE,
    CHECKOUT_COMPLETE,
    REQUEST_PAYMENT,
]
