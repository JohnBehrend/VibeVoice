#!/usr/bin/env python3
"""
Test script to verify speaker tracking functionality in ChapterObj.
"""

from parse_chapter import ChapterObj

def test_speaker_tracking():
    # Create some test ChapterObj instances
    obj1 = ChapterObj(True, "Alice", "Hello there!")
    obj2 = ChapterObj(True, "narrator", "Some narration")
    obj3 = ChapterObj(True, "Bob", "Hi Alice!")
    
    print("Testing speaker tracking functionality:")
    print(f"obj1 speaker: {obj1.get_speaker()}")
    print(f"obj2 speaker: {obj2.get_speaker()}")
    print(f"obj3 speaker: {obj3.get_speaker()}")
    
    # Test setting a speaker reference
    obj2.set_speaker(obj1)  # obj2 should now reference obj1's speaker
    
    print(f"\nAfter setting obj2 to reference obj1:")
    print(f"obj1 speaker: {obj1.get_speaker()}")
    print(f"obj2 speaker: {obj2.get_speaker()}")
    print(f"obj3 speaker: {obj3.get_speaker()}")
    
    # Test with a non-ChapterObj speaker
    obj3.set_speaker("Charlie")
    print(f"\nAfter setting obj3 to 'Charlie':")
    print(f"obj1 speaker: {obj1.get_speaker()}")
    print(f"obj2 speaker: {obj2.get_speaker()}")
    print(f"obj3 speaker: {obj3.get_speaker()}")

if __name__ == "__main__":
    test_speaker_tracking()
