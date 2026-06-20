import os
import re
import pandas as pd
import streamlit as st

# 1. Page Configuration (Must be the very first Streamlit command)
st.set_page_config(page_title="NJ Cost & Price Finder", layout="wide")

# 2. Pure Data Cache (CRITICAL: No 'st.' UI elements allowed inside here!)
@st.cache_data
def load_and_clean_data(file_path):
    df = pd.read_csv(file_path, header=1)
    
    # Reconstruct messy column tiers
    new_cols = []
    for i, col in enumerate(df.columns):
        if 11 <= i <= 19:
            base = col.replace('.1', '').replace('.2', '')
            new_cols.append(f'Supplier Cost ({base})')
        elif 20 <= i <= 28:
            base = col.replace('.1', '').replace('.2', '')
            if base == '100-149': base = '100-249'  # Correct structural typo
            new_cols.append(f'Client Price ({base})')
        elif 29 <= i <= 37:
            base = col.replace('.1', '').replace('.2', '')
            if base == '0-99': base = '50-99'        # Correct structural typo
            new_cols.append(f'Margin ({base})')
        else:
            new_cols.append(col)
            
    df.columns = new_cols

    # Strip currency strings and format floats
    for col in df.columns:
        if any(keyword in col for keyword in ['Cost', 'Price', 'Margin']) or col in ['DELIVERY', 'Sample Fee']:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace('£', '', regex=False).str.replace(',', '', regex=False)
                df[col] = df[col].replace({'TBC': pd.NA, 'nan': pd.NA, 'NaN': pd.NA})
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# Helper functions for the search engine
def parse_search_query(query):
    numbers = re.findall(r'\d+', query)
    quantity = int(numbers[0]) if numbers else None
    product_text = re.sub(r'\d+', '', query).strip()
    return product_text, quantity

def get_tier_bracket(qty):
    if qty is None: return None
    if 50 <= qty <= 99: return '50-99'
    elif 100 <= qty <= 249: return '100-249'
    elif 250 <= qty <= 499: return '250-499'
    elif 500 <= qty <= 999: return '500-999'
    elif 1000 <= qty <= 1999: return '1000-1999'
    elif 2000 <= qty <= 4999: return '2000-4999'
    elif 5000 <= qty <= 9999: return '5000-9999'
    elif 10000 <= qty <= 19999: return '10000-19999'
    elif qty >= 20000: return '20000+'
    return "Under MOQ"

# 3. UI Layout Rendering
st.title("🎯 NJ Internal Product & Cost Finder")
st.write("Type a product keyword and a target quantity to pull real-time supplier costs (e.g., `beanie 250`).")

TARGET_FILE = "NJ AI Pricingcsv.csv"

# Check if the file exists BEFORE running any cached data operations
if not os.path.exists(TARGET_FILE):
    st.error(f"⚠️ **Data File Missing:** Could not find `{TARGET_FILE}` in your GitHub repository folder.")
    st.info("👉 **How to fix this:** Go to your GitHub repository, click 'Add file' -> 'Upload files', and upload the original `NJ AI Pricingcsv.csv` dataset. Once uploaded, this app will start working instantly!")
else:
    try:
        # Load compiled dataset safely
        df_clean = load_and_load_data = load_and_clean_data(TARGET_FILE)
        
        # Main Search Input
        user_input = st.text_input("Search Engine", value="beanie 250", placeholder="e.g., socks 500, hoodie 1500")

        if user_input:
            search_term, target_qty = parse_search_query(user_input)
            tier = get_tier_bracket(target_qty)

            # Filter data based on search
            results = df_clean[
                df_clean['PRODUCT TYPE'].str.contains(search_term, case=False, na=False) |
                df_clean['PRODUCT DESCRIPTION'].str.contains(search_term, case=False, na=False)
            ].copy()

            # Stats Cards
            col1, col2, col3 = st.columns(3)
            col1.metric("Parsed Product Keyword", f'"{search_term}"' if search_term else "All")
            col2.metric("Parsed Quantity Requested", f"{target_qty:,}" if target_qty else "None specified")
            col3.metric("Evaluated Tier Bracket", f"{tier}")

            st.write("---")

            if not results.empty:
                if tier and tier != "Under MOQ":
                    cost_col = f'Supplier Cost ({tier})'
                    price_col = f'Client Price ({tier})'
                    margin_col = f'Margin ({tier})'
                    
                    display_cols = [
                        'PRODUCT TYPE', 'PRODUCT DESCRIPTION', 'SUPPLIER', 'MOQ', 
                        cost_col, price_col, margin_col, 'DELIVERY', 'Bulk Lead Time'
                    ]
                    display_cols = [c for c in display_cols if c in results.columns]
                    
                    final_view = results[display_cols].copy()
                    
                    for c in [cost_col, price_col, margin_col, 'DELIVERY']:
                        if c in final_view.columns:
                            final_view[c] = final_view[c].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) else "TBC")
                    
                    st.subheader(f"Matching results for quantity tier: {tier}")
                    st.dataframe(final_view, use_container_width=True)
                else:
                    if tier == "Under MOQ":
                        st.warning(f"⚠️ The requested quantity ({target_qty}) falls below the standard minimum order quantity requirements.")
                    st.subheader("General Match Results (No Tier Value Applied)")
                    st.dataframe(results[['PRODUCT TYPE', 'PRODUCT DESCRIPTION', 'SUPPLIER', 'MOQ', 'Bulk Lead Time']], use_container_width=True)
            else:
                st.info("No matching products found. Try updating your spelling or search terms.")
                
    except Exception as e:
        st.error(f"An unexpected error occurred while processing the file: {e}")
