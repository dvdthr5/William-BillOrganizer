import tkinter as tk
from tkinter import ttk
from datetime import datetime
import sqlite3
import re
from decimal import Decimal, ROUND_HALF_UP


# Create a database connection and tables
def create_db():
    conn = sqlite3.connect('bills.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY,
            bill_name TEXT,
            price TEXT,
            person TEXT,
            date_time TEXT,
            paid INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS amounts_owed (
            person TEXT PRIMARY KEY,
            amount TEXT
        )
    ''')
    # Initialize amounts owed in the database if not already present
    for person in ['Armando', 'David', 'Noah']:
        c.execute('INSERT OR IGNORE INTO amounts_owed (person, amount) VALUES (?, ?)', (person, '0.00'))
    conn.commit()
    conn.close()

# Initialize the owed amounts
amounts_owed = {'Armando': Decimal('0.00'), 'David': Decimal('0.00'), 'Noah': Decimal('0.00')}

# Function to handle the bill submission
def submit_bill():
    bill_name = bill_name_entry.get()
    price = price_entry.get()
    person = person_var.get()
    date_time = datetime.now().strftime("%m/%d/%Y %H:%M")
    
    # Extract numeric value from price
    price = re.sub('[^0-9.]', '', price)
    try:
        price = Decimal(price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except:
        print("Invalid price entered")
        return
    
    if bill_name and price and person:
        formatted_price = f"${price:.2f}"
        conn = sqlite3.connect('bills.db')
        c = conn.cursor()
        c.execute('INSERT INTO bills (bill_name, price, person, date_time) VALUES (?, ?, ?, ?)',
                  (bill_name, str(price), person, date_time))
        
        # Update amounts owed
        if bill_name.lower() == "rent":
            split_amounts = {'Armando': Decimal('0.35') * price, 'David': Decimal('0.32') * price, 'Noah': Decimal('0.32') * price}
            for p in ['Armando', 'David', 'Noah']:
                if p != person:
                    amounts_owed[p] += split_amounts[p]
                    amounts_owed[person] -= split_amounts[p]
        else:
            split_amount = price / Decimal('3')
            for p in ['Armando', 'David', 'Noah']:
                if p != person:
                    amounts_owed[p] += split_amount
                    amounts_owed[person] -= split_amount
        
        # Save updated amounts owed to the database
        for p in amounts_owed:
            c.execute('REPLACE INTO amounts_owed (person, amount) VALUES (?, ?)', (p, str(amounts_owed[p])))
        
        conn.commit()
        conn.close()
        bills_list.insert('', 'end', values=(bill_name, formatted_price, person, date_time), iid=c.lastrowid)
        bill_name_entry.delete(0, tk.END)
        price_entry.delete(0, tk.END)
        
        update_owed_amounts()
    else:
        print("Please fill all fields")

# Function to load bills from the database
def load_bills():
    conn = sqlite3.connect('bills.db')
    c = conn.cursor()
    c.execute('SELECT id, bill_name, price, person, date_time, paid FROM bills')
    rows = c.fetchall()
    for row in rows:
        try:
            formatted_price = f"${Decimal(row[2]):.2f}"
        except:
            formatted_price = "$0.00"
        bill_id = row[0]
        bill_name = row[1]
        price = formatted_price
        person = row[3]
        date_time = row[4]
        paid = row[5]
        bills_list.insert('', 'end', values=(bill_name, price, person, date_time), iid=bill_id)
        if paid:
            bills_list.item(bill_id, tags=('paid',))
    conn.close()

# Function to load owed amounts from the database
def load_owed_amounts():
    conn = sqlite3.connect('bills.db')
    c = conn.cursor()
    c.execute('SELECT person, amount FROM amounts_owed')
    rows = c.fetchall()
    for row in rows:
        amounts_owed[row[0]] = Decimal(row[1])
    conn.close()
    update_owed_amounts()

# Function to delete the selected bill
def delete_bill():
    selected_item = bills_list.selection()
    if not selected_item:
        print("No item selected")
        return
    bill_id = selected_item[0]
    
    conn = sqlite3.connect('bills.db')
    c = conn.cursor()
    c.execute('DELETE FROM bills WHERE id=?', (bill_id,))
    conn.commit()
    conn.close()
    bills_list.delete(bill_id)

# Function to mark the selected bill as paid
def mark_paid():
    selected_item = bills_list.selection()
    if not selected_item:
        print("No item selected")
        return
    bill_id = selected_item[0]
    
    conn = sqlite3.connect('bills.db')
    c = conn.cursor()
    c.execute('SELECT bill_name, price, person FROM bills WHERE id=?', (bill_id,))
    row = c.fetchone()
    if row:
        bill_name, price, person = row
        price = Decimal(price)
        
        # Adjust amounts owed
        if bill_name.lower() == "rent":
            split_amounts = {'Armando': Decimal('0.35') * price, 'David': Decimal('0.32') * price, 'Noah': Decimal('0.32') * price}
            for p in ['Armando', 'David', 'Noah']:
                if p != person:
                    amounts_owed[p] -= split_amounts[p]
                    amounts_owed[person] += split_amounts[p]
        else:
            split_amount = price / Decimal('3')
            for p in ['Armando', 'David', 'Noah']:
                if p != person:
                    amounts_owed[p] -= split_amount
                    amounts_owed[person] += split_amount
        
        # Save updated amounts owed to the database
        for p in amounts_owed:
            c.execute('REPLACE INTO amounts_owed (person, amount) VALUES (?, ?)', (p, str(amounts_owed[p])))
        
        c.execute('UPDATE bills SET paid=1 WHERE id=?', (bill_id,))
        conn.commit()
    conn.close()
    bills_list.item(bill_id, tags=('paid',))
    update_owed_amounts()

    # Reset amounts owed to zero if no bills are left
    if not bills_list.get_children():
        reset_owed_amounts()

# Function to update the owed amounts display
def update_owed_amounts():
    colors = {'Armando': 'red', 'David': 'green', 'Noah': 'blue'}
    for person in amounts_owed:
        owed_labels[person].config(text=f"{person} owes: ${amounts_owed[person]:.2f}", fg=colors[person])

# Function to reset amounts owed to zero
def reset_owed_amounts():
    conn = sqlite3.connect('bills.db')
    c = conn.cursor()
    for person in amounts_owed:
        amounts_owed[person] = Decimal('0.00')
        c.execute('REPLACE INTO amounts_owed (person, amount) VALUES (?, ?)', (person, '0.00'))
    conn.commit()
    conn.close()
    update_owed_amounts()

# Create the main window
root = tk.Tk()
root.title("William - Bill Collector")

# Create and place labels and entries for bill details
tk.Label(root, text="Bill Name:").grid(row=0, column=0, padx=10, pady=5)
bill_name_entry = tk.Entry(root)
bill_name_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Price:").grid(row=1, column=0, padx=10, pady=5)
price_entry = tk.Entry(root)
price_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Person:").grid(row=2, column=0, padx=10, pady=5)
person_var = tk.StringVar(value="Armando")
persons = ["Armando", "David", "Noah"]
for idx, person in enumerate(persons):
    tk.Radiobutton(root, text=person, variable=person_var, value=person).grid(row=2, column=1+idx, padx=5, pady=5)

# Create and place the submit button
submit_button = tk.Button(root, text="Submit", command=submit_bill)
submit_button.grid(row=3, columnspan=4, pady=10)

# Create and place the delete button
delete_button = tk.Button(root, text="Delete", command=delete_bill)
delete_button.grid(row=3, column=4, padx=10, pady=10)

# Create and place the paid button
paid_button = tk.Button(root, text="Paid", command=mark_paid)
paid_button.grid(row=3, column=5, padx=10, pady=10)

# Create a


columns = ('bill_name', 'price', 'person', 'date_time')
bills_list = ttk.Treeview(root, columns=columns, show='headings')
bills_list.heading('bill_name', text='Bill Name')
bills_list.heading('price', text='Price')
bills_list.heading('person', text='Person')
bills_list.heading('date_time', text='Date and Time')
bills_list.grid(row=4, columnspan=6, pady=10)

# Define tag styles
bills_list.tag_configure('paid', background='lightgreen')

# Create labels to display owed amounts
owed_labels = {}
for idx, person in enumerate(persons):
    owed_labels[person] = tk.Label(root, text=f"{person} owes: $0.00")
    owed_labels[person].grid(row=5, column=idx, padx=10, pady=10)

create_db()
load_bills()
load_owed_amounts()
root.mainloop()