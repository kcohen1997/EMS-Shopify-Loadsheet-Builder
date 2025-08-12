import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import chardet
import threading
import os

processed_df = None
category_mapping = {}
product_file_path = None

def shorten_filename(path, max_length=50):
    filename = os.path.basename(path)
    return filename if len(filename) <= max_length else "..." + filename[-(max_length - 3):]

def update_buttons_state():
    """Enable or disable step 3 and 4 buttons based on file load state."""
    if product_file_path and category_mapping:
        process_button.config(state=tk.NORMAL)
        # Save button stays disabled until processing is done
    else:
        process_button.config(state=tk.DISABLED)
        save_button.config(state=tk.DISABLED)

def load_category_file():
    global category_mapping

    file_path = filedialog.askopenfilename(title="Select Category CSV", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        status_label.config(text="Category file load cancelled.")
        return

    progress_bar.pack(fill='x', padx=20, pady=5)
    progress_bar.start()
    status_label.config(text="Loading category file...")

    def worker():
        global category_mapping
        category_mapping = {}

        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding = chardet.detect(raw_data)['encoding']

            cat_df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

            if 'categoryid' not in cat_df.columns or 'categoryname' not in cat_df.columns:
                root.after(0, lambda: messagebox.showerror(
                    "Category File Error", "Category file must contain 'categoryid' and 'categoryname' columns."))
                root.after(0, lambda: status_label.config(text="Invalid category file."))
                return

            category_mapping = dict(zip(cat_df['categoryid'].astype(str), cat_df['categoryname'].astype(str)))
            root.after(0, lambda: category_filename_label.config(text=f"Category File: {shorten_filename(file_path)}"))
            root.after(0, lambda: status_label.config(text="Category file loaded successfully."))

            root.after(0, update_buttons_state)

        except FileNotFoundError:
            root.after(0, lambda: [
                messagebox.showerror("Category File Error", "Category file not found."),
                status_label.config(text="Category file not found.")
            ])
        except pd.errors.EmptyDataError:
            root.after(0, lambda: [
                messagebox.showerror("Category File Error", "Category file is empty."),
                status_label.config(text="Category file is empty.")
            ])
        except Exception as e:
            root.after(0, lambda: [
                messagebox.showerror("Category File Error", f"Failed to load category file:\n{e}"),
                status_label.config(text="Error loading category file.")
            ])
        finally:
            root.after(0, lambda: [
                progress_bar.stop(),
                progress_bar.pack_forget()
            ])

    threading.Thread(target=worker, daemon=True).start()

def resolve_category_names(ids_str):
    if not isinstance(ids_str, str):
        return ""
    ids = ids_str.split(',')
    names = [
        category_mapping.get(id_.strip(), f"[{id_.strip()}]") 
        for id_ in ids if id_.strip()
    ]
    filtered_names = [
        name for name in names
        if name.lower() != "shop" and not (name.startswith('[') and name.endswith(']'))
    ]
    return ", ".join(filtered_names)

def _process_file_worker(file_path):
    global processed_df
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']

        df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

        required_cols = ['productcode', 'productname', 'ischildofproductcode']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column '{col}' in product file.")

        productcode_to_title = df.set_index('productcode')['productname'].to_dict()
        df['Parent Title'] = df['ischildofproductcode'].map(productcode_to_title)

        child_product_codes = df['ischildofproductcode'].dropna().unique()
        df = df[~df['productcode'].isin(child_product_codes)]

        if 'productprice' in df.columns:
            df['productprice'] = pd.to_numeric(df['productprice'], errors='coerce') \
                .map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")

        if 'categoryids' in df.columns and category_mapping:
            df['Category Names'] = df['categoryids'].map(resolve_category_names)
        else:
            df['Category Names'] = "#N/A"

        final_variant_list = df.copy()
        final_column_list = [
            'productcode', 'productname', 'ischildofproductcode', 'Parent Title', 'productprice',
            'length', 'width', 'height', 'productweight',
            'productdescriptionshort', 'photourl', 'producturl', 'Category Names'
        ]

        for col in final_column_list:
            if col not in final_variant_list.columns:
                final_variant_list[col] = '#N/A'

        final_variant_list = final_variant_list[final_column_list]

        final_variant_list.rename(columns={
            'productcode': 'Part #',
            'productname': 'Full Title',
            'ischildofproductcode': 'Parent #',
            'productprice': 'Retail Price',
            'length': 'Length (in)',
            'width': 'Width (in)',
            'height': 'Height (in)',
            'productweight': 'Weight (in)',
            'productdescriptionshort': 'Description',
            'photourl': 'Image Link',
            'producturl': 'Product Link',
            'Category Names': 'Categories'
        }, inplace=True)

        final_variant_list.fillna("#N/A", inplace=True)
        processed_df = final_variant_list

        root.after(0, lambda: [
            status_label.config(text="Processing complete. You may now save the file."),
            save_button.config(state=tk.NORMAL),
            progress_bar.stop(),
            progress_bar.pack_forget()
        ])

    except FileNotFoundError:
        root.after(0, lambda: [
            status_label.config(text="Error: Product file not found."),
            messagebox.showerror("File Not Found", "The product file could not be found."),
            save_button.config(state=tk.DISABLED),
            progress_bar.stop(),
            progress_bar.pack_forget()
        ])

    except pd.errors.EmptyDataError:
        root.after(0, lambda: [
            status_label.config(text="Error: Product file is empty."),
            messagebox.showerror("Empty File", "The product CSV file is empty."),
            save_button.config(state=tk.DISABLED),
            progress_bar.stop(),
            progress_bar.pack_forget()
        ])

    except ValueError as ve:
        root.after(0, lambda: [
            status_label.config(text=f"Error: {ve}"),
            messagebox.showerror("Invalid Data", str(ve)),
            save_button.config(state=tk.DISABLED),
            progress_bar.stop(),
            progress_bar.pack_forget()
        ])

    except Exception as e:
        root.after(0, lambda: [
            status_label.config(text=f"Unexpected error: {e}"),
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}"),
            save_button.config(state=tk.DISABLED),
            progress_bar.stop(),
            progress_bar.pack_forget()
        ])

def select_product_file():
    global product_file_path
    file_path = filedialog.askopenfilename(title="Select Product CSV", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return

    category_button.config(state=tk.DISABLED)
    process_button.config(state=tk.DISABLED)
    save_button.config(state=tk.DISABLED)

    progress_bar.pack(fill='x', padx=20, pady=5)
    progress_bar.start()
    status_label.config(text="Loading product file...")

    def worker():
        global product_file_path
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding = chardet.detect(raw_data)['encoding']
            df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

            required_cols = ['productcode', 'productname', 'ischildofproductcode']
            for col in required_cols:
                if col not in df.columns:
                    root.after(0, lambda: messagebox.showerror(
                        "Invalid Product File", f"Product file must contain '{col}' column."))
                    root.after(0, lambda: status_label.config(text="Invalid product file."))
                    return

            product_file_path = file_path
            root.after(0, lambda: product_filename_label.config(text=f"Product File: {shorten_filename(file_path)}"))
            root.after(0, lambda: status_label.config(text="Product file loaded. Now select category file."))
            root.after(0, lambda: category_button.config(state=tk.NORMAL))  # Enable category select button

            root.after(0, update_buttons_state)  # Update process/save buttons if conditions met

        except FileNotFoundError:
            root.after(0, lambda: [
                messagebox.showerror("Product File Error", "Product file not found."),
                status_label.config(text="Product file not found.")
            ])
        except pd.errors.EmptyDataError:
            root.after(0, lambda: [
                messagebox.showerror("Product File Error", "Product file is empty."),
                status_label.config(text="Product file is empty.")
            ])
        except Exception as e:
            root.after(0, lambda: [
                messagebox.showerror("Product File Error", f"Failed to load product file:\n{e}"),
                status_label.config(text="Error loading product file.")
            ])
        finally:
            root.after(0, lambda: [
                progress_bar.stop(),
                progress_bar.pack_forget()
            ])

    threading.Thread(target=worker, daemon=True).start()

def process_files():
    if not product_file_path:
        messagebox.showwarning("No Product File", "Please select the product CSV file first.")
        return
    if not category_mapping:
        messagebox.showwarning("No Category File", "Please select the category CSV file first.")
        return

    status_label.config(text="Processing...")
    save_button.config(state=tk.DISABLED)
    progress_bar.pack(fill='x', padx=20, pady=5)
    progress_bar.start()

    threading.Thread(target=_process_file_worker, args=(product_file_path,), daemon=True).start()

def save_file():
    global processed_df
    if processed_df is not None:
        output_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="processed_loadsheet.csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if output_path:
            try:
                processed_df.to_csv(output_path, index=False)
                status_label.config(text="File saved successfully.")
                messagebox.showinfo("Success", f"File saved to:\n{output_path}")
            except PermissionError:
                messagebox.showerror("Permission Error", "The file is open in another program (e.g., Excel). Please close it and try again.")
                status_label.config(text="Error saving file.")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file:\n{e}")
                status_label.config(text="Error saving file.")
        else:
            status_label.config(text="Save cancelled.")
    else:
        messagebox.showwarning("No Data", "No processed data to save.")

# --- GUI Setup ---
root = tk.Tk()
root.title("EMI Loadsheet Builder")
root.geometry("450x320")

product_button = tk.Button(root, text="1. Select Product CSV File", command=select_product_file)
product_button.pack(padx=20, pady=(20, 5))
product_filename_label = tk.Label(root, text="", fg="gray")
product_filename_label.pack(pady=(0, 10))

category_button = tk.Button(root, text="2. Select Category CSV File", command=load_category_file, state=tk.DISABLED)
category_button.pack(padx=20, pady=(5, 10))
category_filename_label = tk.Label(root, text="", fg="gray")
category_filename_label.pack(pady=(0, 10))

process_button = tk.Button(root, text="3. Process Files", command=process_files, state=tk.DISABLED)
process_button.pack(padx=20, pady=(0, 10))

save_button = tk.Button(root, text="4. Save Processed File", command=save_file, state=tk.DISABLED)
save_button.pack(padx=20, pady=(0, 15))

progress_bar = ttk.Progressbar(root, mode='indeterminate')

status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=5)

root.mainloop()
