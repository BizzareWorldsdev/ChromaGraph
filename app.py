from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from textblob import TextBlob
import pandas as pd

app = Flask(__name__)
CORS(app)

YOUTUBE_API_KEY = "YOUR_API_KEY_HERE"

def fetch_comments(video_id):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )
    response = request.execute()

    for item in response.get("items", []):
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "Author": snippet["authorDisplayName"],
            "Comment": snippet["textDisplay"],
            "Likes": snippet["likeCount"],
            "PublishedAt": snippet["publishedAt"]
        })
    return comments

def classify_comment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity

    if polarity <= -0.4:
        return "Hate"
    elif -0.4 < polarity < 0:
        return "Complaint"
    elif polarity >= 0.2:
        return "Good"
    else:
        return "Neutral"

@app.route("/analyze", methods=["POST"])
def analyze_video():
    try:
        data = request.get_json()
        video_id = data.get("video_id")

        if not video_id:
            return jsonify({"error": "Missing video ID"}), 400

        comments = fetch_comments(video_id)
        if not comments:
            return jsonify({"error": "No comments found"}), 404

        for c in comments:
            c["Category"] = classify_comment(c["Comment"])

        df = pd.DataFrame(comments)
        hate_df = df[df["Category"] == "Hate"]
        complaint_df = df[df["Category"] == "Complaint"]
        good_df = df[df["Category"] == "Good"]
        neutral_df = df[df["Category"] == "Neutral"]

        file_path = f"youtube_comments_{video_id}.xlsx"
        with pd.ExcelWriter(file_path) as writer:
            hate_df.to_excel(writer, sheet_name="Hate", index=False)
            complaint_df.to_excel(writer, sheet_name="Complaints", index=False)
            good_df.to_excel(writer, sheet_name="Good", index=False)
            neutral_df.to_excel(writer, sheet_name="Neutral", index=False)

        return jsonify({"message": f"✅ File saved: {file_path}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
