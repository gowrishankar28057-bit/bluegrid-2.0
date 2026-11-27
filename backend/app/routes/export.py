import csv
from html import escape
from io import BytesIO, StringIO
from flask import Blueprint, current_app, abort, Response, send_file

exports = Blueprint("exports", __name__, url_prefix="/api/runs")


def load_run(run_id):
    result = current_app.extensions["run_cache"].get(run_id)
    if result is None:
        abort(404, description="Run not found or expired; evaluate the configuration again")
    return result


@exports.get("/<run_id>/export.json")
def export_json(run_id):
    return Response(current_app.json.dumps(load_run(run_id)), mimetype="application/json",
                    headers={"Content-Disposition": 'attachment; filename="bluegrid-result.json"'})


@exports.get("/<run_id>/export.csv")
def export_csv(run_id):
    result = load_run(run_id)
    output = StringIO(newline="")
    writer = csv.writer(output)
    # Prefix user-authored text so spreadsheet imports cannot interpret it as a formula.
    writer.writerow(["record_type", "field", "value"])
    writer.writerow(["metadata", "synthetic", str(result["provenance"]["synthetic"]).lower()])
    source = result["provenance"]["source"]
    writer.writerow(["metadata", "source", "'" + source if source.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else source])
    writer.writerow([])
    fields = ["timestamps", "demand_kw", "generation_kw", "served_kw", "unmet_kw", "curtailed_kw", "charge_kw", "discharge_kw", "soc_kwh", "loss_kwh"]
    writer.writerow(fields)
    writer.writerows(zip(*(result["hourly"][field] for field in fields)))
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": 'attachment; filename="bluegrid-hourly.csv"'})


@exports.get("/<run_id>/export.pdf")
def export_pdf(run_id):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    result = load_run(run_id)
    stream = BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 11
    styles["Title"].fontSize = 17
    styles["Title"].leading = 21
    story = [Paragraph("BlueGrid 2.0 - Configuration Assessment", styles["Title"]), Spacer(1, 12)]
    def paragraph(value):
        story.append(Paragraph(escape(str(value)), styles["BodyText"]))
        story.append(Spacer(1, 5))
    paragraph("SYNTHETIC DEMONSTRATION" if result["provenance"]["synthetic"] else "USER-PROVIDED RESOURCES - SOURCE NOT INDEPENDENTLY VERIFIED")
    paragraph(result["provenance"]["source"])
    paragraph(f"Run: {run_id} | Period: {result['provenance']['start']} to {result['provenance']['end']}")
    capacity_text = ", ".join(f"{name.replace('_', ' ')}: {capacity:g} kW" for name, capacity in result["configuration"]["capacities_kw"].items() if capacity)
    paragraph(f"Configuration: {capacity_text or 'no generation'}; battery: {result['configuration']['battery_kwh']:g} kWh.")
    paragraph(f"Modeled reliability target: LPSP <= {result['reliability_target']:.2%}. Configuration passes target and wind policy: {result['feasible']}.")
    rows = [["Indicator", "Value"]]
    for name, value in result["metrics"].items():
        rows.append([name, f"{value:,.6g}"])
    for name in ("capex", "annualized_cost", "lcoe", "cost_of_service"):
        value = result["economics"][name]
        unit = result["economics"]["currency"] + ("/kWh" if name in ("lcoe", "cost_of_service") else "/year" if name == "annualized_cost" else "")
        rows.append([f"{name} ({unit})", "undefined" if value is None else f"{value:,.6g}"])
    table = Table(rows, colWidths=[260, 210], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1829")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                               ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([table, Spacer(1, 12)])
    for warning in result["warnings"]:
        paragraph(warning)
    paragraph("LCOE excludes hypothetical backup diesel. Currency/kWh for LCOE and cost of service; currency/year for annualized cost. No independent project certification is implied.")
    SimpleDocTemplate(stream, pagesize=A4, topMargin=32, bottomMargin=32, leftMargin=40, rightMargin=40,
                      title="BlueGrid Configuration Assessment", author="BlueGrid").build(story)
    stream.seek(0)
    return send_file(stream, mimetype="application/pdf", as_attachment=True, download_name="bluegrid-assessment.pdf")
