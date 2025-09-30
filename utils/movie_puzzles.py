"""
Movie puzzle database initialization and management
Handles loading and managing the emoji movie puzzle collection
"""

import json
import logging
from typing import Dict, List, Any
from pathlib import Path

from database.db import DatabaseManager
from database.models import MoviePuzzle, DifficultyLevel

logger = logging.getLogger(__name__)

class MoviePuzzleLoader:
    """Loads and manages movie puzzle database"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def load_puzzles_from_json(self, json_file: str = "movie_puzzles.json"):
        """Load movie puzzles from JSON file into database"""
        try:
            json_path = Path(json_file)
            if not json_path.exists():
                logger.error(f"Puzzle file not found: {json_file}")
                return False

            with open(json_path, 'r', encoding='utf-8') as f:
                puzzle_data = json.load(f)

            total_loaded = 0

            for category, puzzles in puzzle_data.items():
                for i, puzzle_info in enumerate(puzzles):
                    try:
                        puzzle_id = f"{category}_{i+1}"

                        # Check if puzzle already exists
                        existing = await self.db.db.movie_puzzles.find_one({"_id": puzzle_id})
                        if existing:
                            continue  # Skip if already exists

                        puzzle = MoviePuzzle(
                            id=puzzle_id,
                            emojis=puzzle_info["emojis"],
                            answer=puzzle_info["answer"],
                            category=category,
                            difficulty=DifficultyLevel(puzzle_info.get("difficulty", "medium")),
                            hints=puzzle_info.get("hints", [])
                        )

                        await self.db.db.movie_puzzles.insert_one(puzzle.to_dict())
                        total_loaded += 1

                    except Exception as e:
                        logger.error(f"Error loading puzzle {i} from {category}: {e}")
                        continue

            logger.info(f"Loaded {total_loaded} movie puzzles into database")
            return True

        except Exception as e:
            logger.error(f"Error loading puzzles from JSON: {e}")
            return False

    async def create_default_puzzles(self):
        """Create default puzzle collection"""
        try:
            default_puzzles = {
                "hollywood": [
                    {"emojis": "🚢💔🧊", "answer": "Titanic", "difficulty": "easy", "hints": ["1912", "Leonardo DiCaprio", "Unsinkable ship"]},
                    {"emojis": "🦁👑", "answer": "The Lion King", "difficulty": "easy", "hints": ["Disney", "Simba", "Circle of Life"]},
                    {"emojis": "🕷️👦🌃", "answer": "Spider-Man", "difficulty": "easy", "hints": ["Marvel", "Peter Parker", "Web slinger"]},
                    {"emojis": "🤖🚗", "answer": "Transformers", "difficulty": "medium", "hints": ["Autobots", "Robots in disguise", "Optimus Prime"]},
                    {"emojis": "🧙‍♂️👦⚡", "answer": "Harry Potter", "difficulty": "medium", "hints": ["Hogwarts", "Magic", "Boy who lived"]},
                    {"emojis": "🌪️🏠👠", "answer": "The Wizard of Oz", "difficulty": "medium", "hints": ["Dorothy", "Yellow brick road", "There's no place like home"]},
                    {"emojis": "🦇🌆🃏", "answer": "The Dark Knight", "difficulty": "hard", "hints": ["Batman", "Joker", "Why so serious?"]},
                    {"emojis": "🚗⏰", "answer": "Back to the Future", "difficulty": "hard", "hints": ["DeLorean", "Time travel", "1.21 gigawatts"]},
                    {"emojis": "🌌🚀👽", "answer": "Guardians of the Galaxy", "difficulty": "hard", "hints": ["Marvel", "Star-Lord", "I am Groot"]},
                    {"emojis": "🔍🐟", "answer": "Finding Nemo", "difficulty": "easy", "hints": ["Pixar", "Clownfish", "Just keep swimming"]}
                ],
                "bollywood": [
                    {"emojis": "👑💎🏰", "answer": "Mughal-E-Azam", "difficulty": "hard", "hints": ["Historical epic", "Anarkali", "Classic romance"]},
                    {"emojis": "💃🎭❤️", "answer": "Devdas", "difficulty": "medium", "hints": ["Shah Rukh Khan", "Tragic romance", "Paro"]},
                    {"emojis": "🎓📚❤️", "answer": "3 Idiots", "difficulty": "easy", "hints": ["Engineering college", "Aamir Khan", "All is well"]},
                    {"emojis": "🏏🇮🇳🏆", "answer": "83", "difficulty": "medium", "hints": ["Cricket World Cup", "Kapil Dev", "1983 victory"]},
                    {"emojis": "👸💍💔", "answer": "Padmaavat", "difficulty": "hard", "hints": ["Historical drama", "Deepika Padukone", "Sanjay Leela Bhansali"]}
                ],
                "tollywood": [
                    {"emojis": "🗡️👑🏰", "answer": "Baahubali", "difficulty": "medium", "hints": ["Epic movie", "Prabhas", "Why Kattappa killed Baahubali"]},
                    {"emojis": "🎬🎭🎪", "answer": "Arjun Reddy", "difficulty": "hard", "hints": ["Medical student", "Vijay Deverakonda", "Intense romance"]},
                    {"emojis": "🚂💥🔥", "answer": "RRR", "difficulty": "easy", "hints": ["SS Rajamouli", "Ram Charan", "Jr NTR friendship"]}
                ]
            }

            total_created = 0
            for category, puzzles in default_puzzles.items():
                for i, puzzle_info in enumerate(puzzles):
                    puzzle_id = f"{category}_{i+1}"

                    # Check if exists
                    existing = await self.db.db.movie_puzzles.find_one({"_id": puzzle_id})
                    if existing:
                        continue

                    puzzle = MoviePuzzle(
                        id=puzzle_id,
                        emojis=puzzle_info["emojis"],
                        answer=puzzle_info["answer"],
                        category=category,
                        difficulty=DifficultyLevel(puzzle_info["difficulty"]),
                        hints=puzzle_info["hints"]
                    )

                    await self.db.db.movie_puzzles.insert_one(puzzle.to_dict())
                    total_created += 1

            logger.info(f"Created {total_created} default puzzles")
            return True

        except Exception as e:
            logger.error(f"Error creating default puzzles: {e}")
            return False

async def initialize_puzzle_database(db_manager: DatabaseManager):
    """Initialize puzzle database with default data"""
    try:
        loader = MoviePuzzleLoader(db_manager)

        # Try loading from JSON first
        success = await loader.load_puzzles_from_json()

        # If JSON loading fails, create default puzzles
        if not success:
            await loader.create_default_puzzles()

        # Count total puzzles
        count = await db_manager.db.movie_puzzles.count_documents({})
        logger.info(f"Total puzzles in database: {count}")

        return count > 0

    except Exception as e:
        logger.error(f"Error initializing puzzle database: {e}")
        return False
