"""
Test script for greeting detection functionality.

Run this to verify the greeting detector works correctly.
"""

from utils.greeting_detector import greeting_detector


def test_greetings():
    """Test various greeting inputs."""
    test_cases = [
        # English greetings
        ("hi", True, "greeting"),
        ("Hello", True, "greeting"),
        ("Good morning", True, "greeting"),
        ("Hey there", True, "greeting"),

        # English farewells
        ("bye", True, "farewell"),
        ("goodbye", True, "farewell"),
        ("see you later", True, "farewell"),

        # English thanks
        ("thanks", True, "thanks"),
        ("thank you", True, "thanks"),
        ("thanks a lot", True, "thanks"),

        # How are you
        ("how are you", True, "how_are_you"),
        ("how are you doing", True, "how_are_you"),

        # Sinhala greetings
        ("හෙලෝ", True, "greeting"),
        ("ආයුබෝවන්", True, "greeting"),
        ("ස්තූතියි", True, "thanks"),
        ("බායි", True, "farewell"),

        # Tamil greetings
        ("வணக்கம்", True, "greeting"),
        ("நன்றி", True, "thanks"),
        ("பை", True, "farewell"),

        # NOT greetings - real questions
        ("Hi, what is the Dialog helpline number?", False, "none"),
        ("Hello, how do I get a SIM replacement?", False, "none"),
        ("What are the Dialog packages?", False, "none"),
        ("How can I activate roaming?", False, "none"),
        ("Where is the nearest Dialog outlet?", False, "none"),
        ("High speed internet plans", False, "none"),  # contains "hi" but not a greeting

        # Edge cases
        ("", False, "none"),
        ("   ", False, "none"),
    ]

    print("=" * 80)
    print("GREETING DETECTION TEST")
    print("=" * 80)

    passed = 0
    failed = 0

    for query, expected_is_greeting, expected_type in test_cases:
        is_greeting, greeting_type = greeting_detector.is_greeting(query)

        status = "✓ PASS" if (is_greeting == expected_is_greeting and greeting_type == expected_type) else "✗ FAIL"

        if is_greeting == expected_is_greeting and greeting_type == expected_type:
            passed += 1
        else:
            failed += 1

        print(f"\n{status}")
        print(f"  Query: '{query}'")
        print(f"  Expected: is_greeting={expected_is_greeting}, type={expected_type}")
        print(f"  Got:      is_greeting={is_greeting}, type={greeting_type}")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)


if __name__ == "__main__":
    test_greetings()
