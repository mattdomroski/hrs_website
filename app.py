from flask import Flask, redirect, url_for, render_template, request
import settings
import db
import requests
import math
import yaml
app = Flask(__name__)
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return render_template('contact_confirm.html')

    return render_template('contact.html')

#Used for the initial map display before the customer selects their location
DEFAULT_MAP_CENTER = {
    'lat': 34,
    'lng':-111
}
DEFAULT_MAP_ZOOM = 7

LOCATION_SERVICES = {
    1: ['Cabinets', 'Appliances', 'Kitchen Renovations', 'Bath Renovations'],
    2: ['Cabinets', 'Appliances', 'Kitchen Renovations', 'Bath Renovations'],
    3: ['Cabinets', 'Appliances', 'Kitchen Renovations', 'Bath Renovations'],
    4: ['High-End Appliances', 'Bath Renovations'],
    5: ['Home Supply Store']
}

with open('manufacturers.yaml', 'r', encoding='utf-8') as file:
    MANUFACTURERS = yaml.safe_load(file)['manufacturers']
MANUFACTURERS.sort(key=lambda x: x['name'])

with open('categories.yaml', 'r', encoding='utf-8') as file:
    CATEGORIES = yaml.safe_load(file)['categories']

def geocode(**kwargs):
    response = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json',
        params={
            **kwargs,
            'key': settings.GOOGLE_MAPS_API_KEY
        }
    )
    response.raise_for_status()
    return response.json()['results'][0]

def get_address_component(location, component_type):
    return [component for component in location['address_components'] if component_type in component['types']][0]

def get_distance_mi(location1, location2):
    """
    Calculates the distance between two points in miles.
    """

    earth_radius = 3958.8
    phi1, phi2 = math.radians(location1['lat']), math.radians(location2['lat'])
    dphi = math.radians(location2['lat'] - location1['lat'])
    dlambda = math.radians(location2['lng'] - location1['lng'])

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return earth_radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
@app.route('/locations')
def search_locations():
    zip_code = request.args.get('zip', None)
    customer_location = None
    map_center = DEFAULT_MAP_CENTER
    map_zoom = DEFAULT_MAP_ZOOM
    errors = {}
    if zip_code:
        try:
            customer_location = geocode(components=f'postal_code:{zip_code}')
        except Exception:
            errors['zip'] = 'ZIP code not found'
        else:
            country = get_address_component(customer_location, 'country')
            if country['short_name'] != 'US':
                errors['zip'] = f'Unfortunately, {country['long_name']} is outside our service area.'
                customer_location = None
            else:
                state = get_address_component(customer_location, 'administrative_area_level_1')
                if state['short_name'] not in ['AZ', 'NM', 'NV']:
                    errors['zip'] = f'Unfortunately, {state['long_name']} is outside our service area.'
                    customer_location = None

    locations = db.execute(
        sql="SELECT * FROM tbllocations"
    )
    for location in locations:
        location['location'] = geocode(address=f'{location["City"]}, {location["State"]}')['geometry']['location'] #Need fallback
        if customer_location:
            location['distance'] = get_distance_mi(customer_location['geometry']['location'], location['location'])
        location['services'] = LOCATION_SERVICES.get(location['LocationID'], [])

    if customer_location:
        locations.sort(key=lambda x: x['distance'])
        locations[0]['closest'] = True

    return render_template(
        'locations.html',
        locations=locations,
        map_center=map_center,
        map_zoom=map_zoom,
        zip=zip_code,
        customer_location=customer_location,
        errors=errors,
        google_maps_api_key=settings.GOOGLE_MAPS_API_KEY
    )

def inventory_items_subquery(location):
    args = [
        "ii.ProductID = p.ProductID",
        "ItemStatus = 'In Stock'"
    ]
    if location:
        args.append("LocationID = %(location)s")

    return f"(SELECT COUNT(InventoryItemID) FROM tblinventoryitems ii WHERE {' AND '.join(args)})"

@app.route('/products')
def list_products():
    filters = []
    args = {}

    category = request.args.get('category', None)
    if category:
        filters.append('Category = %(category)s')
        args['category'] = category

    manufacturer = request.args.get('manufacturer', None)
    if manufacturer:
        filters.append('Brand = %(manufacturer)s')
        args['manufacturer'] = manufacturer

    location = request.args.get('location', None)
    if location:
        try:
            location = int(location)
        except ValueError:
            pass
        else:
            args['location'] = location

    stock = request.args.get('stock', None)
    if stock == 'on':
        filters.append(f"{inventory_items_subquery(location)} > 0")

    where_clause = f'WHERE {' AND '.join(filters)}' if filters else ''

    products = db.execute(sql=f"""
        SELECT
            *,
            {inventory_items_subquery(location)} AS stock
        FROM tblproducts p {where_clause}
    """,
    args=args
    )
    keyed_manufacturers = {m['name']: m for m in MANUFACTURERS}
    for product in products:
        product['manufacturer'] = keyed_manufacturers.get(product['Brand'], None)
    locations = db.execute(
        sql="SELECT * FROM tbllocations"
    )

    return render_template(
        'products.html',
        products=products,
        categories=CATEGORIES,
        category=category,
        manufacturers=MANUFACTURERS,
        manufacturer=manufacturer,
        locations=locations,
        location=location,
        stock=stock
    )

@app.route('/manufacturers')
def list_manufacturers():
    return render_template('manufacturers.html', manufacturers=MANUFACTURERS)

@app.route('/categories')
def list_categories():
    for category in CATEGORIES:
        category['image_url'] = url_for('static', filename=f'assets/category-images/{category['slug']}.png')
    return render_template('categories.html', categories=CATEGORIES)

@app.route('/receipts')
def receipts():
    id_type = request.args.get('id_type')
    order_or_job_id = request.args.get('id')
    email = request.args.get('email')
    errors = {
        'id_type': '',
        'id': '',
        'email': ''
    }

    if id_type or order_or_job_id or email:
        if not id_type:
            errors['id_type'] = 'An option must be selected.'
            return render_template('receipts.html', args=request.args, errors=errors)

        if not order_or_job_id:
            errors['id'] = 'A value must be entered.'
            return render_template('receipts.html', args=request.args, errors=errors)

        if not email:
            errors['email'] = 'A value must be entered.'
            return render_template('receipts.html', args=request.args, errors=errors)

        try:
            order_or_job_id = int(order_or_job_id)
        except ValueError:
            errors['id'] = 'ID must be an integer.'

        customers = db.execute(
            sql='SELECT CustomerID FROM tblcustomers WHERE LOWER(Email) = %(email)s',
            args={'email': email.strip().lower()}
        )
        if len(customers) == 0:
            errors['email'] = 'A customer with this email does not exist.'
            return render_template('receipts.html', args=request.args, errors=errors)

        if id_type == 'order':
            orders = db.execute(
                sql="""
                    SELECT
                        o.OrderID AS 'Order ID',
                        o.OrderDate AS 'Order Date',
                        o.OrderStatus AS 'Order Status',                        
                        CONCAT(c.FirstName, ' ', c.LastName) AS 'Customer Name',                        
                        c.Phone AS 'Customer Phone',
                        c.Email AS 'Customer Email',
                        CONCAT(
                            c.Street, ', ',
                            c.City, ', ',
                            c.State, ' ',
                            c.Zip
                        ) AS 'Customer Address',
                        l.LocationName AS Location,
                        CONCAT(e.FirstName, ' ', e.LastName, ', ', e.JobTitle) AS Employee,
                        CONCAT('$', (SELECT SUM(UnitPrice * Quantity) FROM tblOrderDetails WHERE OrderID = o.OrderID)) AS 'Item Total',
                        CONCAT('$', o.DeliveryCharge) AS 'Delivery Charge',
                        CONCAT(o.TaxRate * 100, '%%') AS 'Tax Rate',
                        CONCAT('$', ROUND(((SELECT SUM(UnitPrice * Quantity) FROM tblOrderDetails WHERE OrderID = o.OrderID) + o.DeliveryCharge) * (1 + o.TaxRate), 2)) AS 'Order Total',
                        CONCAT('$', (SELECT SUM(Amount) FROM tblPayments WHERE OrderId = o.OrderId)) AS 'Total Paid',
                        CONCAT('$', ROUND((
                            (((SELECT SUM(UnitPrice * Quantity) FROM tblOrderDetails WHERE OrderID = o.OrderID) + o.DeliveryCharge) * (1 + o.TaxRate))
                             - (SELECT SUM(Amount) FROM tblPayments WHERE OrderId = o.OrderId)
                        ), 2)) AS 'Amount Due'
                    FROM tblorders o
                    JOIN tblcustomers c ON o.CustomerID = c.CustomerID
                    JOIN tbllocations l ON o.LocationID = l.LocationID
                    JOIN tblemployees e ON o.employeeID = e.EmployeeID
                    WHERE OrderID = %(order_id)s
                    AND c.CustomerID IN %(customer_ids)s
                """,
                args={
                    'order_id': order_or_job_id,
                    'customer_ids': [customer['CustomerID'] for customer in customers]
                }
            )
            if len(orders) == 0:
                errors['id'] = 'An order with this id does not exist.'
                return render_template('receipts.html', args=request.args, errors=errors)

            order_items = db.execute(
                sql="""
                    SELECT
                        Brand,
                        ProductDescription AS 'Description',
                        Category,
                        ModelNumber AS 'Model Number',
                        Quantity,
                        CONCAT('$', UnitPrice) AS ' Unit Price'                      
                    FROM tblorderdetails oi
                    JOIN tblproducts p ON oi.productID = p.ProductID
                    WHERE oi.OrderID = %(order_id)s
                """,
                args={'order_id': order_or_job_id}
            )
            item_headers = set().union(*order_items)

            payments = db.execute(
                sql="""
                    SELECT
                        PaymentDate AS 'Payment Date',
                        PaymentMethod AS 'Payment Method',
                        Amount
                    FROM tblpayments
                    WHERE OrderID = %(order_id)s
                """,
                args={'order_id': order_or_job_id}
            )
            payment_headers = set().union(*payments)

            return render_template(
                'order_receipt.html',
                order=orders[0],
                order_items=order_items,
                item_headers=item_headers,
                payments=payments,
                payment_headers=payment_headers
            )

        if id_type == 'job':
            #TODO
            pass


    return render_template('receipts.html', args=request.args, errors=errors)

@app.route('/login')
def login():
    return redirect(settings.STAFF_PORTAL_URL)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
