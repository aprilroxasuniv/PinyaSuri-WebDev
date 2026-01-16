import random

def analyze_image(image_path):
    """
    Dummy AI analyzer
    Input: image_path (string)
    Output: dict (AI analysis result)
    """

    pineapple_detected = random.randint(5, 15)
    black_rot = random.randint(0, 5)
    healthy = random.randint(5, 20)

    return {
        "analysis": {
            "pineapple_detected": pineapple_detected,
            "black_rot": black_rot,
            "healthy": healthy
        },
        "confidence": round(random.uniform(0.85, 0.98), 2),
        "status": "success"
    }
