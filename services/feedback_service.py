import time
import os

# Import Google GenAI SDK
try:
    from google import genai

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class FeedbackService:
    def __init__(self, db):
        self.db = db
        self.gemini_client = None
        if HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
            try:
                self.gemini_client = genai.Client(
                    api_key=os.environ.get("GEMINI_API_KEY")
                )
            except Exception:
                pass

    def submit_feedback(self, scores, comments):
        """Saves a feedback submission containing ratings and comment."""
        feedback = {
            "id": f"feedback-{time.time()}",
            "scores": {
                "navigation": int(scores.get("navigation", 5)),
                "food": int(scores.get("food", 5)),
                "restrooms": int(scores.get("restrooms", 5)),
                "security": int(scores.get("security", 5)),
                "ai_assistant": int(scores.get("ai_assistant", 5)),
            },
            "comments": str(comments)[:500],
            "timestamp": time.time(),
        }

        if self.db.use_firebase:
            try:
                self.db.db.collection("feedbacks").document(
                    feedback["id"]
                ).set(feedback)
            except Exception as e:
                print(f"[FeedbackService] Firebase write error: {e}")
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                if "feedbacks" not in data:
                    data["feedbacks"] = []
                data["feedbacks"].append(feedback)
                self.db._write_local_db(data)
        return feedback

    def get_feedbacks(self):
        """Retrieves all submitted feedbacks."""
        if self.db.use_firebase:
            try:
                docs = self.db.db.collection("feedbacks").stream()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"[FeedbackService] Firebase read error: {e}")
                return []
        else:
            with self.db.lock:
                data = self.db._read_local_db()
                return data.get("feedbacks", [])

    def generate_feedback_summary(self):
        """Uses Gemini to summarize the fan experience and feedback."""
        feedbacks = self.get_feedbacks()
        if not feedbacks:
            return "No feedback has been submitted by fans yet. Check back once attendees register ratings."

        # Aggregate averages
        count = len(feedbacks)
        avg_scores = {
            "navigation": 0.0,
            "food": 0.0,
            "restrooms": 0.0,
            "security": 0.0,
            "ai_assistant": 0.0,
        }
        comments = []
        for f in feedbacks:
            scores = f["scores"]
            for key in avg_scores:
                avg_scores[key] += scores.get(key, 5)
            if f.get("comments"):
                comments.append(f["comments"])

        for key in avg_scores:
            avg_scores[key] = round(avg_scores[key] / count, 1)

        comments_summary = "\n".join([f"- {c}" for c in comments[:10]])

        prompt = f"""
        You are ArenaFlow's Operations Analyst 🤖. Summarize the following fan satisfaction metrics and comments:
        - Total Feedback Submissions: {count}
        - Average Ratings (out of 5 stars):
          * Navigation: {avg_scores['navigation']}
          * Food: {avg_scores['food']}
          * Restrooms: {avg_scores['restrooms']}
          * Security: {avg_scores['security']}
          * AI Assistant: {avg_scores['ai_assistant']}

        Recent Comments:
        {comments_summary}

        Generate a concise, professional report (3 bullet points maximum) summarizing:
        1. Current areas of high satisfaction.
        2. Friction points (e.g. food queues, navigation difficulties).
        3. Recommended operations adjustments (e.g. dispatch staff, change routes).
        Use Markdown formatting (bolding).
        """

        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-1.5-flash", contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"[FeedbackService] Gemini error: {e}")

        # Local rule-based summary fallback
        lowest_cat = min(avg_scores, key=avg_scores.get)
        highest_cat = max(avg_scores, key=avg_scores.get)

        fallback_summary = (
            f"### Operations Feedback Summary 🤖\n\n"
            f"**Key Findings**:\n"
            f"- **Highest Rated Category**: *{highest_cat.capitalize()}* is performing best with an average rating of **{avg_scores[highest_cat]}/5**.\n"
            f"- **Core Friction Point**: *{lowest_cat.capitalize()}* represents the lowest rated metric at **{avg_scores[lowest_cat]}/5** and needs operations focus.\n\n"
            f"**Recommended Adjustments**:\n"
            f"- Redeploy security and medical staff to areas experiencing low satisfaction scores.\n"
            f"- Advise the AI Concierge to route fans away from bottleneck concourses.\n\n"
            f"*(Generated via local operations summary engine)*"
        )
        return fallback_summary
