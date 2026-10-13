from datetime import datetime
from html import escape

import requests
import streamlit as st

import db
import ebay
import ship24
from finance import net_profit

API_ERRORS = (requests.RequestException, RuntimeError)
STATUS_LABELS = {
    "pending": "To pack",
    "label_created": "Label ready",
    "shipped": "On the way",
    "delivered": "Delivered",
    "returned": "Returned",
}
EBAY_COLUMNS = {
    "item_id": "Item",
    "title": "Title",
    "price": "Price",
    "watchers": "Watchers",
    "url": st.column_config.LinkColumn("Link", display_text="Open"),
    "offer": "Offer",
    "buyer": "Buyer",
    "message": "Message",
    "expires": "Expires",
    "order_id": "Order",
    "date": "Date",
    "items": "Items",
    "total": "Total",
    "ebay_fee": "eBay fee",
    "payment": "Payment",
    "fulfillment": "Fulfilment",
}


def eur(amount):
    return f"−€{-amount:,.2f}" if amount < 0 else f"€{abs(amount):,.2f}"  # abs: no "-0.00"


def headline(listings, sold):
    to_pack = sum(s["status"] == "pending" for s in sold)
    on_the_way = sum(s["status"] in ("label_created", "shipped") for s in sold)
    made = sum(
        net_profit(s["sale_price"], s["cost_price"], s["fee_pct"], s["fee_fixed"], s["shipping_cost"])[1]
        for s in sold
        if s["status"] != "returned"
    )
    parts = []
    if listings:
        parts.append(f"{len(listings)} listing{'' if len(listings) == 1 else 's'} live")
    if to_pack:
        parts.append(f"{to_pack} to pack")
    if on_the_way:
        parts.append(f"{on_the_way} on the way")
    if sold:
        parts.append(f"{eur(made)} made")
    return ", ".join(parts) + "." if parts else "Nothing listed yet."


def receipt(listing, sale_price, shipping_cost):
    fee, net, margin = net_profit(
        sale_price, listing["cost_price"], listing["fee_pct"], listing["fee_fixed"], shipping_cost
    )
    discount = listing["list_price"] - sale_price
    if discount > 0:
        against_asking = f"{eur(discount)} under asking"
    elif discount < 0:
        against_asking = f"{eur(-discount)} over asking"
    else:
        against_asking = "at asking price"
    lines = [
        ("Buyer pays", sale_price),
        (f"{listing['platform']} fee", -fee),
        ("You paid", -listing["cost_price"]),
        ("Shipping", -shipping_cost),
    ]
    rows = "".join(
        f'<div class="receipt-line"><dt>{escape(label)}</dt><dd>{eur(amount)}</dd></div>'
        for label, amount in lines
    )
    return f"""
    <div class="receipt-wrap"><div class="receipt">
      <p class="receipt-title">{escape(listing["title"])}</p>
      <p class="receipt-note">{escape(listing["platform"])}, asking {eur(listing["list_price"])}</p>
      <dl>{rows}</dl>
      <p class="receipt-total"><span>You keep</span>
        <span class="{"loss" if net < 0 else "gain"}">{eur(net)}</span></p>
      <p class="receipt-note">{margin:.1f}% margin, {against_asking}</p>
    </div></div>
    """


def journey(status):
    steps = db.SHIPMENT_STATUSES[:-1]  # returned is not a step
    items = ""
    for index, step in enumerate(steps):
        if index < steps.index(status):
            items += f'<li class="done">{STATUS_LABELS[step]}</li>'
        elif step == status:
            items += f'<li class="now" aria-current="step">{STATUS_LABELS[step]}</li>'
        else:
            items += f"<li>{STATUS_LABELS[step]}</li>"
    return f'<ol class="journey">{items}</ol>'


st.set_page_config(page_title="Logistics Tracker", page_icon=":material/checkroom:", layout="wide")
st.html(db.ROOT / "style.css")
db.init()
settings = db.settings()
listings = db.active_listings()

st.title(headline(listings, db.sold_listings()), anchor=False)
inventory_tab, profit_tab, shipping_tab, ebay_tab, settings_tab = st.tabs(
    ["Inventory", "Profit", "Shipping", "eBay", "Settings"]
)

with inventory_tab:
    platforms = db.query("SELECT * FROM platforms ORDER BY name")
    form_column, table_column = st.columns([1, 2], gap="large")

    with form_column, st.form("add_listing", clear_on_submit=True):
        st.subheader("New listing", anchor=False)
        title = st.text_input("Title")
        left, right = st.columns(2)
        brand = left.text_input("Brand")
        size = right.text_input("Size")
        platform = st.selectbox("Platform", [p["name"] for p in platforms])
        left, right = st.columns(2)
        cost_price = left.number_input("You paid (€)", min_value=0.0, step=0.5)
        list_price = right.number_input("Asking price (€)", min_value=0.0, step=0.5)
        if st.form_submit_button("Add listing", type="primary"):
            if not title.strip() or list_price <= 0:
                st.error("Give it a title and an asking price above €0.")
            else:
                db.add_listing(title.strip(), brand.strip(), size.strip(), platform, cost_price, list_price)
                st.rerun()

    with table_column:
        st.subheader("Live listings", anchor=False)
        if listings:
            rows = [
                {
                    "title": row["title"],
                    "brand": row["brand"],
                    "size": row["size"],
                    "platform": row["platform"],
                    "cost_price": row["cost_price"],
                    "list_price": row["list_price"],
                    "margin": net_profit(
                        row["list_price"], row["cost_price"], row["fee_pct"], row["fee_fixed"]
                    )[2],
                    "listed": datetime.fromisoformat(row["created_at"]).date(),
                }
                for row in listings
            ]
            st.dataframe(
                rows,
                hide_index=True,
                column_config={
                    "title": "Title",
                    "brand": "Brand",
                    "size": "Size",
                    "platform": "Platform",
                    "cost_price": st.column_config.NumberColumn("You paid", format="€%.2f"),
                    "list_price": st.column_config.NumberColumn("Asking", format="€%.2f"),
                    "margin": st.column_config.ProgressColumn(
                        "Margin at asking", min_value=0, max_value=100, format="%.0f%%"
                    ),
                    "listed": st.column_config.DateColumn("Listed", format="D MMM"),
                },
            )
        else:
            st.info("Nothing listed yet. Add your first listing with the form.")

        with st.expander("Platform fees"):
            fees = st.data_editor(
                platforms,
                hide_index=True,
                disabled=["name"],
                column_config={
                    "name": "Platform",
                    "fee_pct": st.column_config.NumberColumn("Fee %", min_value=0.0),
                    "fee_fixed": st.column_config.NumberColumn("Fixed fee (€)", min_value=0.0),
                },
            )
            if st.button("Save fees"):
                for fee in fees:
                    db.execute(
                        "UPDATE platforms SET fee_pct = ?, fee_fixed = ? WHERE name = ?",
                        (fee["fee_pct"], fee["fee_fixed"], fee["name"]),
                    )
                st.rerun()

with profit_tab:
    if not listings:
        st.info("Add a listing in Inventory to work out its profit.")
    else:
        controls, result = st.columns([2, 3], gap="large")
        with controls:
            listing = st.selectbox(
                "Listing",
                listings,
                format_func=lambda row: f"{row['title']} ({row['platform']}, {eur(row['list_price'])})",
            )
            # keyed per listing so the offer resets to that listing's price
            sale_price = st.number_input(
                "Buyer's offer (€)",
                min_value=0.0,
                value=listing["list_price"],
                step=0.5,
                key=f"offer_{listing['id']}",
            )
            shipping_cost = st.number_input(
                "Shipping you pay (€)", min_value=0.0, step=0.5, key=f"shipping_{listing['id']}"
            )
            if st.button("Mark sold at this price", type="primary", disabled=sale_price <= 0):
                db.mark_sold(listing["id"], sale_price, shipping_cost)
                st.rerun()
        result.html(receipt(listing, sale_price, shipping_cost))

with shipping_tab:
    shipments = db.shipments()
    if not shipments:
        st.info("No parcels yet. Mark a listing as sold in Profit and it shows up here.")
    else:
        st.dataframe(
            [
                {
                    **{key: "" if value is None else value for key, value in row.items()},
                    "status": STATUS_LABELS[row["status"]],
                    "updated_at": row["updated_at"][:10],
                }
                for row in shipments
            ],
            hide_index=True,
            column_order=[
                "title", "platform", "sale_price", "status", "carrier",
                "tracking_number", "last_event", "shipping_cost", "updated_at",
            ],
            column_config={
                "title": "Title",
                "platform": "Platform",
                "sale_price": st.column_config.NumberColumn("Sold for", format="€%.2f"),
                "status": "Status",
                "carrier": "Carrier",
                "tracking_number": "Tracking number",
                "last_event": "Latest event",
                "shipping_cost": st.column_config.NumberColumn("Shipping", format="€%.2f"),
                "updated_at": "Updated",
            },
        )

        form_column, tracking_column = st.columns(2, gap="large")
        with form_column:
            st.subheader("Update a parcel", anchor=False)
            shipment = st.selectbox(
                "Parcel",
                shipments,
                format_func=lambda row: f"{row['title']} ({STATUS_LABELS[row['status']]})",
            )
            with st.form(f"shipment_{shipment['id']}"):
                status = st.selectbox(
                    "Status",
                    db.SHIPMENT_STATUSES,
                    index=db.SHIPMENT_STATUSES.index(shipment["status"]),
                    format_func=STATUS_LABELS.get,
                )
                carrier = st.text_input("Carrier", shipment["carrier"] or "")
                tracking_number = st.text_input("Tracking number", shipment["tracking_number"] or "")
                if st.form_submit_button("Save parcel"):
                    db.update_shipment(shipment["id"], status, carrier.strip(), tracking_number.strip())
                    st.rerun()

        with tracking_column:
            st.subheader(shipment["title"], anchor=False)
            if shipment["status"] == "returned":
                st.warning("This parcel came back to you.")
            else:
                st.html(journey(shipment["status"]))

            api_key = settings.get("ship24_api_key")
            events_key = f"events_{shipment['id']}"
            if not api_key:
                st.caption("Add a Ship24 key in Settings to check tracking from here.")
            elif not shipment["tracking_number"]:
                st.caption("Save a tracking number to check tracking.")
            if st.button("Check tracking", disabled=not (api_key and shipment["tracking_number"])):
                try:
                    with st.spinner("Asking Ship24..."):
                        milestone, events = ship24.track(api_key, shipment["tracking_number"])
                except API_ERRORS as error:
                    st.error(str(error))
                else:
                    last_event = milestone
                    if events:
                        when = events[0]["occurrenceDatetime"][:16].replace("T", " ")
                        last_event = f"{when} {events[0]['status']}"
                    status = ship24.MILESTONE_STATUS.get(milestone, shipment["status"])
                    db.update_tracking(shipment["id"], status, last_event)
                    st.session_state[events_key] = events
                    st.rerun()
            if st.session_state.get(events_key):
                columns = {"occurrenceDatetime": "When", "status": "What", "location": "Where"}
                st.dataframe(
                    [{c: event.get(c) for c in columns} for event in st.session_state[events_key]],
                    hide_index=True,
                    column_config=columns,
                )

with ebay_tab:
    ebay_keys = [settings.get(k) for k in ("ebay_client_id", "ebay_client_secret", "ebay_refresh_token")]
    if not all(ebay_keys):
        st.info("Connect your eBay account in Settings to see your listings, offers and orders here.")
    else:
        if st.button("Refresh from eBay", type="primary"):
            try:
                with st.spinner("Asking eBay..."):
                    token = ebay.access_token(*ebay_keys)
                    st.session_state["ebay"] = {
                        "Active listings": ebay.active_listings(token),
                        "Best offers": ebay.best_offers(token),
                        "Orders": ebay.orders(token),
                    }
            except API_ERRORS as error:
                st.error(str(error))
        for heading, rows in st.session_state.get("ebay", {}).items():
            st.subheader(heading, anchor=False)
            if rows:
                st.dataframe(rows, hide_index=True, column_config=EBAY_COLUMNS)
            else:
                st.caption("Nothing here right now.")

with settings_tab:
    keys_column, ebay_column = st.columns(2, gap="large")

    with keys_column, st.form("settings"):
        st.subheader("Your keys", anchor=False)
        st.caption("Saved in tracker.db on this computer only. Never share or commit that file.")
        ship24_api_key = st.text_input(
            "Ship24 API key", settings.get("ship24_api_key", ""), type="password"
        )
        client_id = st.text_input("eBay App ID (Client ID)", settings.get("ebay_client_id", ""))
        client_secret = st.text_input(
            "eBay Cert ID (Client Secret)", settings.get("ebay_client_secret", ""), type="password"
        )
        runame = st.text_input("eBay RuName", settings.get("ebay_runame", ""))
        if st.form_submit_button("Save keys", type="primary"):
            db.save_settings({
                "ship24_api_key": ship24_api_key.strip(),
                "ebay_client_id": client_id.strip(),
                "ebay_client_secret": client_secret.strip(),
                "ebay_runame": runame.strip(),
            })
            st.rerun()

    with ebay_column:
        st.subheader("eBay account", anchor=False)
        client_id, client_secret, runame = (
            settings.get(k) for k in ("ebay_client_id", "ebay_client_secret", "ebay_runame")
        )
        if settings.get("ebay_refresh_token"):
            st.success("Your eBay account is connected.")
            if st.button("Disconnect eBay"):
                db.save_settings({"ebay_refresh_token": ""})
                st.session_state.pop("ebay", None)
                st.rerun()
        elif not (client_id and client_secret and runame):
            st.info("Save your eBay App ID, Cert ID and RuName first.")
        else:
            st.link_button("1. Sign in to eBay and agree", ebay.consent_url(client_id, runame))
            redirect = st.text_input("2. Paste the address of the page you land on (it contains code=)")
            if st.button("3. Connect", disabled=not redirect.strip()):
                try:
                    code = ebay.code_from_redirect(redirect)
                    refresh_token = ebay.exchange_code(client_id, client_secret, runame, code)
                except API_ERRORS as error:
                    st.error(str(error))
                else:
                    db.save_settings({"ebay_refresh_token": refresh_token})
                    st.rerun()
