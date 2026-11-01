from flask import Flask, redirect, url_for, render_template, request
import settings
import db

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

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/locations')
def locations():
    return render_template('locations.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

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
            sql='SELECT CustomerID FROM tblCustomers WHERE LOWER(Email) = %(email)s',
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
                    FROM tblOrders o
                    JOIN tblCustomers c ON o.CustomerID = c.CustomerID
                    JOIN tblLocations l ON o.LocationID = l.LocationID
                    JOIN tblEmployees e ON o.employeeID = e.EmployeeID
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
                    FROM tblOrderDetails oi
                    JOIN tblProducts p ON oi.productID = p.ProductID
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
                    FROM tblPayments
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
