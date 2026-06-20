import os
import re
import pandas as pd
import streamlit as st

# 1. Page Configuration
st.set_page_config(page_title="NJ Cost & Price Finder", layout="wide")

# 2. Cached Data Loader for Excel
@st.cache_data
def load_clean_excel(file_path):
    df = pd.read_excel(file_path)
    return df

# Helper functions for query parsing
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

# Expected filename
TARGET_FILE = "Cleaned_NJ_AI_Pricing.xlsx"

# Check if the file exists on GitHub before loading
if not os.path.exists(TARGET_FILE):
    st.error(f"⚠️ **Excel File Missing:** Could not find `{TARGET_FILE}` in your GitHub repository.")
    st.info("👉 **How to fix this:** Upload your `Cleaned_NJ_AI_Pricing.xlsx` file directly to the root of your GitHub repository. Make sure the filename matches exactly (case-sensitive).")
else:
    try:
        # Load the pre-cleaned data cleanly
        df_clean = load_clean_excel(TARGET_FILE)
        
        # Search Box
        user_input = st.text_input("Search Engine", value="beanie 250", placeholder="e.g., socks 500, hoodie 1500")

        if user_input:
            search_term, target_qty = parse_search_query(user_input)
            tier = get_tier_bracket(target_qty)

            # Filter rows where Product Type or Description matches the keyword
            results = df_clean[
                df_clean['PRODUCT TYPE'].str.contains(search_term, case=False, na=False) |
                df_clean['PRODUCT DESCRIPTION'].str.contains(search_term, case=False, na=False)
            ].copy()

            # Dynamic Metrics Display
            col1, col2, col3 = st.columns(3)
            col1.metric("Parsed Product Keyword", f'"{search_term}"' if search_term else "All")
            col2.metric("Parsed Quantity Requested", f"{target_qty:,}" if target_qty else "None specified")
            col3.metric("Evaluated Tier Bracket", f"{tier}")

            st.write("---")

            if not results.empty:
                # If a valid quantity tier matches, show specific pricing metrics
                if tier and tier != "Under MOQ":
                    cost_col = f'Supplier Cost ({tier})'
                    price_col = f'Client Price ({tier})'
                    margin_col = f'Margin ({tier})'
                    
                    # Group relevant columns for presentation
                    display_cols = [
                        'PRODUCT TYPE', 'PRODUCT DESCRIPTION', 'SUPPLIER', 'MOQ', 
                        cost_col, price_col, margin_col, 'DELIVERY', 'Bulk Lead Time'
                    ]
                    # Filter out any missing metadata columns dynamically
                    display_cols = [c for c in display_cols if c in results.columns]
                    
                    final_view = results[display_cols].copy()
                    
                    # Clean look currency formatting
                    for c in [cost_col, price_col, margin_col, 'DELIVERY']:
                        if c in final_view.columns:
                            final_view[c] = final_view[c].apply(lambda x: f"£{x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else f"£{x}" if pd.notna(x) else "TBC")
                    
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
        st.error(f"An unexpected error occurred while parsing the Excel file: {e}")
