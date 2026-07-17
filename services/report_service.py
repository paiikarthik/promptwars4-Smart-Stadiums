import os
import time
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ReportService")

# Try to import fpdf for PDF exports
try:
    from fpdf import FPDF

    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

# Try to import Google GenAI SDK
try:
    from google import genai
    import google.api_core.exceptions

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class ReportService:
    """Service class responsible for generating incident reports and Operations Copilot chat answers.

    Attributes:
        db (Any): Stadium database interface helper.
        gemini_client (Optional[genai.Client]): GenAI client session if configured.
    """

    def __init__(self, db: Any) -> None:
        """Initializes ReportService with database and Gemini configurations.

        Args:
            db (Any): Stadium database client.
        """
        self.db: Any = db
        self.gemini_client: Optional[genai.Client] = None
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                self.gemini_client = genai.Client(
                    api_key=os.environ.get("GEMINI_API_KEY")
                )
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[ReportService] Gemini initialization error: {e}")

    def _format_telemetry_summary(self, state: Dict[str, Any]) -> Tuple[int, str, str]:
        """Formats current crowd, gate wait times, and zone density summaries.

        Args:
            state (Dict[str, Any]): Current telemetry state mapping.

        Returns:
            Tuple[int, str, str]: Total occupancy, gate statuses, and zone densities.
        """
        total_occupancy: int = state.get("occupancy", 0)
        gates_str: str = ", ".join(
            [
                f"{g['name']}: {g['waitTimeMinutes']}m wait"
                for g in state.get("gates", [])
            ]
        )
        zones_str: str = ", ".join(
            [
                f"{z['name']}: {z['crowdLevel']}% full"
                for z in state.get("zones", [])
            ]
        )
        return total_occupancy, gates_str, zones_str

    def _format_recent_logs(self, dispatches: List[Dict[str, Any]], alerts: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Formats lists of recent dispatches and alerts for reports.

        Args:
            dispatches (List[Dict[str, Any]]): Recorded dispatches log.
            alerts (List[Dict[str, Any]]): Broadcasted alerts list.

        Returns:
            Tuple[str, str]: Markdown formatted strings of logs.
        """
        recent_dispatches = dispatches[:5]
        dispatch_str = (
            "\n".join(
                [
                    f"- Deployed {d['staff_type'].capitalize()} to Zone {d['zone_id']} at {time.strftime('%H:%M:%S', time.localtime(d['timestamp']))}"
                    for d in recent_dispatches
                ]
            )
            if recent_dispatches
            else "- No dispatches recorded"
        )

        recent_alerts = alerts[:5]
        alerts_str = (
            "\n".join(
                [
                    f"- [{a['type'].upper()}] {a['message']}"
                    for a in recent_alerts
                ]
            )
            if recent_alerts
            else "- No alerts broadcasted"
        )
        return dispatch_str, alerts_str

    def generate_incident_report_text(self) -> str:
        """Compiles incident metrics and requests Gemini to create an AI summary.

        Returns:
            str: Markdown format operations incident report.
        """
        state: Dict[str, Any] = self.db.get_simulation_state()
        alerts: List[Dict[str, Any]] = self.db.get_alerts()
        dispatches: List[Dict[str, Any]] = self.db.get_dispatches()

        total_occupancy, gates_str, zones_str = self._format_telemetry_summary(state)
        dispatch_str, alerts_str = self._format_recent_logs(dispatches, alerts)

        prompt = f"""
        You are ArenaFlow's Incident & Command Chief Operations Officer 🤖.
        Compile an Operations Incident Report based on current telemetry:
        - Current Crowd: {total_occupancy} / {state.get('capacity', 70000)}
        - Entrances: {gates_str}
        - Concourse Zones: {zones_str}
        - Dispatch Logs:
        {dispatch_str}
        - Alert Broadcast History:
        {alerts_str}

        Format a professional incident report:
        1. **Executive Summary**: General status of the stadium.
        2. **Peak Congestion & Risks**: Key bottlenecks (e.g. zones above 80% or gates above 15 mins).
        3. **Critical Events & Dispatches**: Analysis of dispatches and broadcast alerts.
        4. **AI Recommended Actions**: Operational changes required (e.g. gate redirections, staff deployment).
        Keep it clean and readable in Markdown.
        """

        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-1.5-flash", contents=prompt
                )
                res_text: str = response.text
                return res_text
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[ReportService] Gemini report generation error: {e}")

        # Local rule-based fallback generator
        congested = [
            z["name"] for z in state.get("zones", []) if z["crowdLevel"] > 75
        ]
        congested_str = ", ".join(congested) if congested else "None"

        fallback_report = (
            f"### ARENAFLOW INCIDENT REPORT 📋\n\n"
            f"**1. Executive Summary**:\n"
            f"- Stadium status is stable. Current attendance is **{total_occupancy}** (Capacity: {state.get('capacity', 70000)}).\n\n"
            f"**2. Peak Congestion & Risks**:\n"
            f"- High congestion detected in: **{congested_str}**.\n"
            f"- Alert and dispatch activity indicates moderate crowd flow strain.\n\n"
            f"**3. Critical Events & Dispatches**:\n"
            f"- Total registered dispatches: **{len(dispatches)}**.\n"
            f"- Active notifications: **{len(alerts)}**.\n\n"
            f"**4. Recommended Actions**:\n"
            f"- Re-route incoming fans from busy concourses to clearer gates.\n"
            f"- Maintain standby medical teams near high-density food stands.\n\n"
            f"*(Report compiled via local operations reporting engine)*"
        )
        return fallback_report

    def _pdf_add_header(self, pdf: Any, title: str) -> None:
        """Adds operational brand header banner to FPDF document.

        Args:
            pdf (FPDF): FPDF instance.
            title (str): Title of the report.
        """
        pdf.set_fill_color(18, 22, 41)
        pdf.rect(0, 0, 210, 40, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", size=18)
        pdf.cell(0, 10, "ARENAFLOW OPERATIONS COMMAND", ln=1, align="C")
        pdf.set_font("Arial", size=12)
        pdf.cell(
            0,
            10,
            f"Report Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            ln=1,
            align="C",
        )
        pdf.ln(15)

        # Body settings
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", size=14)
        pdf.cell(0, 10, title.replace("_", " "), ln=1)
        pdf.set_font("Arial", size=11)
        pdf.ln(5)

    def export_report_to_pdf(self, report_text: str, title: str = "Incident_Report") -> Optional[bytes]:
        """Compiles FPDF document and returns raw bytes of PDF.

        Args:
            report_text (str): Report text.
            title (str): Output PDF file name/header.

        Returns:
            Optional[bytes]: raw bytes of compiled PDF document, or None if FPDF is missing.
        """
        if not HAS_FPDF:
            return None

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        self._pdf_add_header(pdf, title)

        lines = report_text.split("\n")
        for line in lines:
            cleaned = line.replace("**", "").replace("*", "").strip()
            if not cleaned:
                pdf.ln(4)
                continue

            try:
                pdf.multi_cell(
                    0, 6, cleaned.encode("latin1", "ignore").decode("latin1")
                )
            except (UnicodeEncodeError, UnicodeDecodeError):
                pdf.multi_cell(0, 6, cleaned)

        val_bytes: bytes = pdf.output(dest="S")
        return val_bytes

    def _get_local_copilot_response(self, question: str, state: Dict[str, Any]) -> str:
        """Processes simple queries through rule-based matching.

        Args:
            question (str): User command.
            state (Dict[str, Any]): Telemetry snapshot.

        Returns:
            str: Preformatted assistant answer.
        """
        q = question.lower()
        if "cause" in q or "congestion" in q or "busy" in q:
            congested = [
                z["name"]
                for z in state.get("zones", [])
                if z["crowdLevel"] > 75
            ]
            if congested:
                return f"📋 **Copilot**: The current congestion is primarily located in **{', '.join(congested)}** due to high flow rates. Staff dispatches may be required to manage queues."
            return "📋 **Copilot**: Concourse levels are currently normal; no significant bottlenecks are detected."

        if "gate" in q or "wait" in q:
            gates = state.get("gates", [])
            if gates:
                slowest = max(gates, key=lambda x: x["waitTimeMinutes"])
                return f"📋 **Copilot**: **{slowest['name']}** currently has the highest wait time at **{slowest['waitTimeMinutes']} minutes**."
            return "📋 **Copilot**: Gate wait metrics are currently unavailable."

        if "staff" in q or "recommend" in q:
            zones = state.get("zones", [])
            if zones:
                busiest = max(zones, key=lambda x: x["crowdLevel"])
                return (
                    f"📋 **Copilot Staffing Alert**:\n"
                    f"- Recommend deploying **Security** to **{busiest['name']}** (Current density: {busiest['crowdLevel']}%).\n"
                    f"- Maintain medical standbys near gate entrances to assist inbound flows."
                )

        return "📋 **Copilot**: I can analyze stadium metrics and alerts. Ask me about congestion causes, gate wait peaks, or staffing recommendations."

    def run_operations_copilot(self, question: str) -> str:
        """AI Operations Copilot: Answers questions about operations using telemetry.

        Args:
            question (str): User command message.

        Returns:
            str: Markdown format answer.
        """
        state: Dict[str, Any] = self.db.get_simulation_state()
        alerts = self.db.get_alerts()
        dispatches = self.db.get_dispatches()

        summary_data = {
            "current_occupancy": state.get("occupancy"),
            "gates_wait": [
                {"name": g["name"], "wait": g["waitTimeMinutes"]}
                for g in state.get("gates", [])
            ],
            "zones_crowd": [
                {"name": z["name"], "density": z["crowdLevel"]}
                for z in state.get("zones", [])
            ],
            "total_alerts": len(alerts),
            "total_dispatches": len(dispatches),
            "last_dispatch": dispatches[0] if dispatches else None,
        }

        prompt = f"""
        You are ArenaFlow's Operations Command Copilot 🤖.
        Your task is to answer operational queries for administrators based on the current metrics and logs:

        {json.dumps(summary_data, indent=2)}

        User Question: {question}

        Answer the user's question with precise details. If they ask for:
        - "What caused congestion?" -> Highlight the zones with crowd levels >75% and review recent dispatches/alerts.
        - "Which gate has the highest wait?" -> Inspect gates lists.
        - "Generate staffing recommendations" -> Propose deploying security/medical staff based on the highest zone density.

        Keep your response brief (1-2 paragraphs), analytical, and objective. Use Markdown tags.
        """

        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-1.5-flash", contents=prompt
                )
                res_text: str = response.text
                return res_text
            except google.api_core.exceptions.GoogleAPIError as e:
                logger.error(f"[ReportService] Copilot Gemini error: {e}")

        return self._get_local_copilot_response(question, state)
