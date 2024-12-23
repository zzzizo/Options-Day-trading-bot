import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from ib_insync import *
from datetime import datetime, timedelta
import threading
import asyncio

# Global variables for IB instance and trading control
ib = None
trading_active = False
buy_threshold = 100
sell_threshold = 110
manual_contract_size = 1
manual_expiration = '20250119'

# Function to connect to IB Gateway
def connect_to_gateway():
    global ib
    ib = IB()
    try:
        ib.connect('127.0.0.1', 4002, clientId=1)
        status_var.set("Connected")
        status_label.config(fg="#4CAF50")
        messagebox.showinfo("Success", "Connected to IB Gateway!")
    except Exception as e:
        status_var.set("Not Connected")
        status_label.config(fg="#F44336")
        messagebox.showerror("Error", f"Connection failed: {e}")

# Start trading function
def start_trading():
    global trading_active, manual_expiration, manual_contract_size

    symbol = stock_entry.get().strip()
    expiration_date = expiration_entry.get().strip()
    contract_size = contract_size_entry.get().strip()

    if not symbol or not expiration_date or not contract_size:
        messagebox.showerror("Error", "Please enter all required fields: Symbol, Expiration, and Contract Size.")
        return

    try:
        manual_contract_size = int(contract_size)
        manual_expiration = expiration_date
    except ValueError:
        messagebox.showerror("Error", "Contract size must be a valid number.")
        return

    trading_active = True
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    log_message(f"Trading started for stock: {symbol}.")

    trading_thread = threading.Thread(target=trade_options, args=(symbol,))
    trading_thread.daemon = True
    trading_thread.start()

# Stop trading function
def stop_trading():
    global trading_active
    trading_active = False
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    log_message("Trading stopped.")

# Trade options logic
def trade_options(symbol):
    global trading_active, manual_contract_size, manual_expiration
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        stock = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(stock)

        option = Option(symbol, manual_expiration, 100, 'C', 'SMART')
        option.multiplier = manual_contract_size
        ib.qualifyContracts(option)

        # Update contract details on the dashboard
        update_contract_details(option)

        def on_tick_update(ticker):
            if not trading_active:
                return
            current_price = ticker.last
            if current_price is not None:
                root.after(100, update_status, f"Current Price: {current_price}")

                if current_price < buy_threshold:
                    place_order(option, "BUY", current_price, symbol)
                elif current_price > sell_threshold:
                    place_order(option, "SELL", current_price, symbol)

        ib.reqMktData(stock, '', False, False, on_tick_update)

        # Keep the loop running while trading is active
        while trading_active:
            ib.sleep(1)

        ib.cancelMktData(stock)  # Cancel market data subscription when done

    except Exception as e:
        messagebox.showerror("Error", f"Trading error: {e}")

# Place order function
def place_order(option, action, price, symbol):
    try:
        order = LimitOrder(action, manual_contract_size, price)
        trade = ib.placeOrder(option, order)

        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        while not trade.isDone():
            ib.sleep(1)

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        benefit = calculate_benefit(action, price)

        log_message(f"{action} order completed for stock {symbol} at {price}. Start: {start_time}, End: {end_time}, Benefit: {benefit}")

    except Exception as e:
        log_message(f"Failed to place {action} order for stock {symbol}: {e}")

# Calculate benefit function (placeholder)
def calculate_benefit(action, price):
    return "TBD"

# Update contract details on the dashboard
def update_contract_details(option):
    contract = ib.reqContractDetails(option)
    if contract:
        details = contract[0]
        contract_details.set(
            f"Symbol: {option.symbol}\n"
            f"Expiration: {manual_expiration}\n"
            f"Strike: {option.strike}\n"
            f"Right: {option.right}\n"
            f"Exchange: {option.exchange}\n"
            f"Contract Size: {manual_contract_size}"
        )
    else:
        contract_details.set("Unable to retrieve contract details.")

# Log message function
def log_message(message):
    today = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"{today}.txt"

    with open(log_filename, "a") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{timestamp}] {message}\n")
    update_status(message)

# Update status label
def update_status(message):
    status_var.set(message)

# Set thresholds function
def set_parameters():
    global buy_threshold, sell_threshold
    try:
        buy_threshold = float(buy_entry.get().strip())
        sell_threshold = float(sell_entry.get().strip())
        messagebox.showinfo("Success", "Parameters updated successfully!")
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numeric values for thresholds.")

# Create the GUI
root = tk.Tk()
root.title("Day Trading CALL Options Bot")
root.geometry("400x600")

# Configure style
style = ttk.Style()
style.configure('TFrame', background='#f5f5f5')
style.configure('TLabel', background='#f5f5f5', font=('Segoe UI', 9))
style.configure('TEntry', font=('Segoe UI', 9))
style.configure('TButton', font=('Segoe UI', 9))

# Main container
main_frame = ttk.Frame(root, padding="20 20 20 20", style='TFrame')
main_frame.pack(fill=tk.BOTH, expand=True)

# Bot Settings Frame
settings_frame = ttk.LabelFrame(main_frame, text="Bot Settings", padding="10 10 10 10")
settings_frame.pack(fill=tk.X, pady=(0, 10))

# Stock Name
ttk.Label(settings_frame, text="Stock Name:").pack(anchor=tk.W)
stock_entry = ttk.Entry(settings_frame, width=30)
stock_entry.pack(fill=tk.X, pady=(0, 10))

# Expiration Date
ttk.Label(settings_frame, text="Expiration Date (YYYY-MM-DD):").pack(anchor=tk.W)
expiration_entry = ttk.Entry(settings_frame, width=30)
expiration_entry.pack(fill=tk.X, pady=(0, 10))

# Buy Threshold
ttk.Label(settings_frame, text="Buy %:").pack(anchor=tk.W)
buy_entry = ttk.Entry(settings_frame, width=30)
buy_entry.pack(fill=tk.X, pady=(0, 10))

# Trailing Stop
ttk.Label(settings_frame, text=" Sell %:").pack(anchor=tk.W)
sell_entry = ttk.Entry(settings_frame, width=30)
sell_entry.pack(fill=tk.X, pady=(0, 10))

# Number of Contracts
ttk.Label(settings_frame, text="Number of Contracts:").pack(anchor=tk.W)
contract_size_entry = ttk.Entry(settings_frame, width=30)
contract_size_entry.pack(fill=tk.X, pady=(0, 10))

# Status
ttk.Label(settings_frame, text="Status:").pack(anchor=tk.W)
status_var = tk.StringVar(value="Not Connected")
status_label = ttk.Label(settings_frame, textvariable=status_var, foreground="#F44336")
status_label.pack(anchor=tk.W, pady=(0, 10))

# Contract Details Frame
contract_frame = ttk.LabelFrame(main_frame, text="Contract Details", padding="10 10 10 10")
contract_frame.pack(fill=tk.X, pady=(0, 10))

contract_details = tk.StringVar(value="No contract details available.")
contract_details_label = ttk.Label(contract_frame, textvariable=contract_details)
contract_details_label.pack(anchor=tk.W)

# Buttons Frame
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=10)

# Trading Control Buttons
control_frame = ttk.LabelFrame(main_frame, text="Trading Controls", padding="10 10 10 10")
control_frame.pack(fill=tk.X, pady=(0, 10))

button_frame = ttk.Frame(control_frame)
button_frame.pack(fill=tk.X, pady=(0, 5))

start_button = ttk.Button(button_frame, text="Start Trading", command=start_trading)
start_button.pack(side=tk.LEFT, padx=(0, 5))

stop_button = ttk.Button(button_frame, text="Stop Trading", command=stop_trading, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT)

connect_button = ttk.Button(control_frame, text="Connect to IB Gateway", command=connect_to_gateway)
connect_button.pack(fill=tk.X, pady=(5, 0))

# Start the event loop
root.mainloop()

# Disconnect from IB when closing
if ib:
    ib.disconnect()