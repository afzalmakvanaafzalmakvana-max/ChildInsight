"""
Research-backed cognitive and educational activities organized by age band.
Covers children aged 4-14 across 5 categories:
- Visual Learning (visual)
- Logic (logic)
- Numbers (numbers)
- Language (language)
- Memory (memory)

Developmental Age Bands:
- Ages 4-6: colour/shape matching, simple picture memory, alphabet recognition, basic counting, sorting by size/colour (Beginner / Easy)
- Ages 6-9: pattern completion, odd-one-out, number sequences, basic arithmetic, word matching, vocabulary, sequence memory (Easy / Medium)
- Ages 9-12: number-grid logic puzzles (simplified sudoku), word association/synonym-antonym games, logical sequence puzzles, riddle-style clue questions (Medium / Advanced)
- Ages 12-14: harder logic puzzles, reading comprehension challenges, complex pattern recognition, multi-step problem-solving (Advanced)

Tone is strictly playful, exploratory, and game-like — never exam-like or worksheet-like.
"""

SEED_CATEGORIES = [
    # =========================================================================
    # 1. VISUAL LEARNING
    # =========================================================================
    {
        'name': 'Visual Learning',
        'slug': 'visual',
        'icon': '🎨',
        'description': 'Develop color discrimination, spatial awareness, and shape identification skills.',
        'activities': [
            # --- Ages 4-6 ---
            {
                'title': 'Color Match Adventure [Demo Data]',
                'description': 'Help the painter mix magical colors and spot shapes in nature!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'What magical new color appears when you mix sunny yellow and bright red together?',
                        'options': ['Orange', 'Blue', 'Green', 'Purple'],
                        'answer': 'Orange',
                        'hint': 'Think of a juicy citrus fruit or a pumpkin!'
                    },
                    {
                        'text': 'Which friendly shape has 3 straight sides and 3 pointy corners?',
                        'options': ['Triangle', 'Square', 'Circle', 'Rectangle'],
                        'answer': 'Triangle',
                        'hint': 'Count 1, 2, 3 points like a slice of pizza.'
                    },
                    {
                        'text': 'Which color shines like the warm summer sun in the sky?',
                        'options': ['Yellow', 'Grey', 'Brown', 'Black'],
                        'answer': 'Yellow',
                        'hint': 'It is bright and cheerful like a sunflower.'
                    }
                ]
            },
            {
                'title': 'Shape Explorer [Demo Data]',
                'description': 'Go on a treasure hunt to discover round, flat, and blocky shapes all around!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which shape has 4 straight sides that are all the exact same size?',
                        'options': ['Square', 'Circle', 'Triangle', 'Oval'],
                        'answer': 'Square',
                        'hint': 'Think of a picture frame or a building block.'
                    },
                    {
                        'text': 'How many sharp corners does a smooth round bubble or circle have?',
                        'options': ['0', '1', '3', '4'],
                        'answer': '0',
                        'hint': 'Circles curve gently all the way around without any points!'
                    },
                    {
                        'text': 'What shape is a bright full moon shining in the night sky?',
                        'options': ['Circle', 'Star', 'Heart', 'Diamond'],
                        'answer': 'Circle',
                        'hint': 'It looks like a glowing round coin.'
                    }
                ]
            },
            {
                'title': 'Rainbow Sorting Quest [Demo Data]',
                'description': 'Sort colorful toys and discover warm and cool colors in the toy chest!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which of these colors feels cool like a calm ocean or a clear pond?',
                        'options': ['Blue', 'Red', 'Orange', 'Bright Yellow'],
                        'answer': 'Blue',
                        'hint': 'Look at the color of water and waves.'
                    },
                    {
                        'text': 'If you arrange these circles by size from biggest to smallest, which comes first?',
                        'options': ['Giant Beach Ball', 'Tennis Ball', 'Tiny Marble', 'Golf Ball'],
                        'answer': 'Giant Beach Ball',
                        'hint': 'Find the one you could hug with two arms!'
                    },
                    {
                        'text': 'Which sweet berry wears a bright coat of red?',
                        'options': ['Strawberry', 'Blueberry', 'Blackberry', 'Grape'],
                        'answer': 'Strawberry',
                        'hint': 'It has tiny seeds on the outside and a green leafy hat.'
                    }
                ]
            },
            {
                'title': 'Tiny Critter Camouflage [Demo Data]',
                'description': 'Spot cute hidden animals by matching patterns, stripes, and spots!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which wild friend hides in tall grass with bold black and white stripes?',
                        'options': ['Zebra', 'Lion', 'Bear', 'Elephant'],
                        'answer': 'Zebra',
                        'hint': 'It looks like a horse wearing striped pajamas!'
                    },
                    {
                        'text': 'Which tiny bug wears bright red wings with fun black polka dots?',
                        'options': ['Ladybug', 'Ant', 'Grasshopper', 'Spider'],
                        'answer': 'Ladybug',
                        'hint': 'Children love when this spotted beetle lands on their hand!'
                    },
                    {
                        'text': 'A chameleon sits on a green jungle leaf. What color does it turn to blend in?',
                        'options': ['Green', 'Hot Pink', 'Purple', 'Neon Blue'],
                        'answer': 'Green',
                        'hint': 'It matches the color of the leaf perfectly.'
                    }
                ]
            },

            # --- Ages 6-9 ---
            {
                'title': 'Pattern Spotter [Demo Data]',
                'description': 'Follow playful color tracks and visual sequences to find the missing piece!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Look at this train track pattern: Red, Blue, Red, Blue, ___. What comes next?',
                        'options': ['Red', 'Blue', 'Yellow', 'Green'],
                        'answer': 'Red',
                        'hint': 'Follow the repeating back-and-forth rhythm.'
                    },
                    {
                        'text': 'Which item does not belong in this group of geometric shapes?',
                        'options': ['Juicy Apple', 'Circle', 'Square', 'Triangle'],
                        'answer': 'Juicy Apple',
                        'hint': 'One is a delicious fruit, the others are drawing shapes.'
                    },
                    {
                        'text': 'Look at the arrows: Up, Right, Up, Right, Up, ___. Which way turns next?',
                        'options': ['Right', 'Down', 'Left', 'Up'],
                        'answer': 'Right',
                        'hint': 'The arrows alternate between skyward and forward.'
                    }
                ]
            },
            {
                'title': 'Odd-One-Out Safari [Demo Data]',
                'description': 'Use your eagle eyes to spot which shape or symbol behaves differently!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Which shape has four sides while all the others have three sides?',
                        'options': ['Rectangle', 'Equilateral Triangle', 'Right Triangle', 'Isosceles Triangle'],
                        'answer': 'Rectangle',
                        'hint': 'Count the edges on each one.'
                    },
                    {
                        'text': 'Look at these clock hands: 12:00, 3:00, 6:00, 7:14. Which one is not on an exact hour?',
                        'options': ['7:14', '12:00', '3:00', '6:00'],
                        'answer': '7:14',
                        'hint': 'The odd one does not have :00 at the end.'
                    },
                    {
                        'text': 'Which creature has six legs while all the other companions have eight legs?',
                        'options': ['Butterfly', 'Spider', 'Octopus', 'Scorpion'],
                        'answer': 'Butterfly',
                        'hint': 'Insects have 6 legs; arachnids have 8.'
                    }
                ]
            },
            {
                'title': 'Symmetry Spark [Demo Data]',
                'description': 'Discover mirror reflections and discover shapes that look identical on both sides!',
                'difficulty': 'Medium',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'If you fold a butterfly painting down the middle, what happens to the wings?',
                        'options': ['They match perfectly like a mirror', 'One wing is missing', 'The colors turn black', 'They become a circle'],
                        'answer': 'They match perfectly like a mirror',
                        'hint': 'Symmetry means both sides reflect each other.'
                    },
                    {
                        'text': 'Which capital letter has a vertical line of symmetry down its middle: A, F, G, or J?',
                        'options': ['A', 'F', 'G', 'J'],
                        'answer': 'A',
                        'hint': 'Split it right in half from top to bottom and both sides match.'
                    },
                    {
                        'text': 'How many lines of symmetry does a plain square piece of origami paper have?',
                        'options': ['4', '1', '2', '0'],
                        'answer': '4',
                        'hint': 'You can fold it in half vertically, horizontally, and along both diagonals.'
                    }
                ]
            },
            {
                'title': 'Geometric Builder [Demo Data]',
                'description': 'Piece together smaller flat tiles to craft brand new shapes and mosaics!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'If you put two identical triangles together along their long side, what shape can you form?',
                        'options': ['A Diamond / Parallelogram', 'A Circle', 'A Crescent', 'A Sphere'],
                        'answer': 'A Diamond / Parallelogram',
                        'hint': 'Think of two triangular puzzle pieces locking into a four-sided gem.'
                    },
                    {
                        'text': 'How many small squares of size 1x1 are needed to fill a bigger 2x2 square?',
                        'options': ['4', '2', '6', '8'],
                        'answer': '4',
                        'hint': 'Two on top and two on the bottom: 2 times 2!'
                    },
                    {
                        'text': 'What shape do you get if you slice a cylinder straight across its flat top?',
                        'options': ['A Circle', 'A Triangle', 'A Star', 'A Cube'],
                        'answer': 'A Circle',
                        'hint': 'Look at the top lid of a soup can.'
                    }
                ]
            },

            # --- Ages 9-12 ---
            {
                'title': 'Spatial Navigator [Demo Data]',
                'description': 'Mentally rotate 3D objects, unfold paper cubes, and explore architecture!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'If you unfold a cardboard cube into a flat net, how many square faces will it have?',
                        'options': ['6', '4', '8', '12'],
                        'answer': '6',
                        'hint': 'Top, bottom, front, back, left, and right sides.'
                    },
                    {
                        'text': 'Looking at a cone directly from above, what 2D shape does your eye observe?',
                        'options': ['A Circle with a center point', 'A Triangle', 'A Square', 'A Hexagon'],
                        'answer': 'A Circle with a center point',
                        'hint': 'You see the round circular base and the very tip right in the center.'
                    },
                    {
                        'text': 'If you rotate an "L" shape 90 degrees clockwise, which direction does its bottom foot point?',
                        'options': ['Downwards', 'To the left', 'Upwards', 'Diagonally'],
                        'answer': 'Downwards',
                        'hint': 'Turn your head a quarter turn to the right.'
                    }
                ]
            },
            {
                'title': '3D Cube Rotation [Demo Data]',
                'description': 'Imagine holding a wooden block puzzle in your mind and rotating it around!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'A cube has a star on top and a circle on the bottom. If you flip it completely upside down, where is the star?',
                        'options': ['On the bottom', 'On the front', 'On the top', 'On the right side'],
                        'answer': 'On the bottom',
                        'hint': 'A full flip reverses top and bottom.'
                    },
                    {
                        'text': 'How many small 1x1x1 cubes are needed to build a solid 3x3x3 Rubik-style block?',
                        'options': ['27', '9', '18', '36'],
                        'answer': '27',
                        'hint': 'Multiply length x width x height: 3 x 3 x 3.'
                    },
                    {
                        'text': 'How many corners (vertices) does a solid rectangular prism have in total?',
                        'options': ['8', '6', '12', '4'],
                        'answer': '8',
                        'hint': '4 corners on the ceiling, 4 corners on the floor.'
                    }
                ]
            },
            {
                'title': 'Optical Illusion Detective [Demo Data]',
                'description': 'Decipher clever visual tricks, hidden silhouettes, and perspective illusions!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'In the famous vase/faces illusion, what happens when you switch your focus from white to black?',
                        'options': ['You see two profiles looking at each other instead of a vase', 'The image vanishes', 'The colors start glowing', 'It turns into a staircase'],
                        'answer': 'You see two profiles looking at each other instead of a vase',
                        'hint': 'The brain alternates between figure and background.'
                    },
                    {
                        'text': 'Two train tracks appear to get narrower in the far distance. Why do they look closer together?',
                        'options': ['Perspective illusion (vanishing point)', 'The tracks actually shrink', 'The train gets smaller', 'Gravity bends them'],
                        'answer': 'Perspective illusion (vanishing point)',
                        'hint': 'Objects further away appear smaller on your visual horizon.'
                    },
                    {
                        'text': 'In the Müller-Lyer illusion, which line appears longer to the eye even when both are identical length?',
                        'options': ['The line with outward-pointing arrow tails (<--->)', 'The line with inward-pointing arrow heads (>---<)', 'Both look like dots', 'Neither line is visible'],
                        'answer': 'The line with outward-pointing arrow tails (<--->)',
                        'hint': 'Outward-pointing fins make the segment appear to stretch outward.'
                    }
                ]
            },
            {
                'title': 'Grid Map Treasure Hunt [Demo Data]',
                'description': 'Track pirate coordinates and navigate top-down treasure maps using spatial clues!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Starting at grid coordinate (2, 3), if Captain Jack walks 3 steps East (+x) and 2 steps North (+y), where is he?',
                        'options': ['(5, 5)', '(3, 5)', '(5, 3)', '(2, 6)'],
                        'answer': '(5, 5)',
                        'hint': 'Add 3 to the first number (2+3=5) and 2 to the second (3+2=5).'
                    },
                    {
                        'text': 'If facing North, what compass direction is directly over your left shoulder (90 degrees counter-clockwise)?',
                        'options': ['West', 'East', 'South', 'North-East'],
                        'answer': 'West',
                        'hint': 'Remember: Never Eat Soggy Waffles (North, East, South, West).'
                    },
                    {
                        'text': 'On a contour elevation map, what does it mean when the circular brown lines are packed very tightly together?',
                        'options': ['The hill or cliff is very steep', 'The ground is completely flat', 'There is deep water', 'It is a sandy beach'],
                        'answer': 'The hill or cliff is very steep',
                        'hint': 'Rapid elevation changes squeeze the height lines together.'
                    }
                ]
            },

            # --- Ages 12-14 ---
            {
                'title': 'Complex Matrix Reasoning [Demo Data]',
                'description': 'Crack multi-rule visual matrices where shapes rotate, shade, and change simultaneously!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In a 3x3 matrix, row 1 rotates 45 deg, row 2 rotates 90 deg. What rotation step rule governs row 3?',
                        'options': ['135 degrees (increasing by 45 deg each row)', '0 degrees', '10 degrees', '360 degrees'],
                        'answer': '135 degrees (increasing by 45 deg each row)',
                        'hint': 'Notice the arithmetic progression: +45, +90, +135.'
                    },
                    {
                        'text': 'Rule 1: Circle inside square. Rule 2: Triangle inside circle. Rule 3: Square inside triangle. What pattern is happening?',
                        'options': ['The outer shape becomes the inner shape of the next frame', 'Shapes disappear', 'Colors invert', 'Sides double every step'],
                        'answer': 'The outer shape becomes the inner shape of the next frame',
                        'hint': 'Trace which shape moves to the inside position.'
                    },
                    {
                        'text': 'In a visual logic puzzle, if white XOR black equals black, and black XOR black equals white, what does white XOR white yield?',
                        'options': ['White (identical states cancel out)', 'Black', 'Striped', 'Transparent'],
                        'answer': 'White (identical states cancel out)',
                        'hint': 'XOR keeps only differing regions and clears matching ones.'
                    }
                ]
            },
            {
                'title': 'Origami Geometry Lab [Demo Data]',
                'description': 'Predict crease patterns and hole punch locations after multi-layer paper folds!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'A square sheet is folded in half horizontally, then in half vertically. A hole is punched through all layers. When unfolded, how many holes appear?',
                        'options': ['4 holes', '2 holes', '1 hole', '8 holes'],
                        'answer': '4 holes',
                        'hint': 'Each fold doubles the layer count: 1 -> 2 -> 4 layers.'
                    },
                    {
                        'text': 'If you punch the hole right along the folded center spine of that twice-folded sheet, where will the holes end up?',
                        'options': ['Symmetrically arranged around the center', 'Only in the top-left corner', 'In a single straight diagonal line', 'Scattered randomly'],
                        'answer': 'Symmetrically arranged around the center',
                        'hint': 'Both fold lines reflect around the paper center point.'
                    },
                    {
                        'text': 'What geometric shape is created when a regular hexagon is folded precisely along its three main diagonals?',
                        'options': ['6 equilateral triangles', '4 squares', '8 circles', '2 pentagons'],
                        'answer': '6 equilateral triangles',
                        'hint': 'A hexagon can be partitioned into six identical equilateral wedges.'
                    }
                ]
            },
            {
                'title': 'Cross-Section Architect [Demo Data]',
                'description': 'Slice through 3D architectural solids to reveal fascinating 2D geometric cross-sections!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'If you slice a solid cube with a flat plane passing through three non-adjacent corners, what cross-section polygon do you see?',
                        'options': ['An equilateral triangle', 'A perfect circle', 'A trapezoid', 'A pentagon'],
                        'answer': 'An equilateral triangle',
                        'hint': 'Connecting three corners cuts a clean triangular slice.'
                    },
                    {
                        'text': 'What cross-section shape results from slicing a circular cone at a slight slant through its curved side, without hitting the base?',
                        'options': ['An ellipse (oval)', 'A parabola', 'A hyperbola', 'A triangle'],
                        'answer': 'An ellipse (oval)',
                        'hint': 'A slanted closed cut across a cone creates an ellipse.'
                    },
                    {
                        'text': 'Can a flat slice through a standard 3D cube produce a 6-sided regular hexagon?',
                        'options': ['Yes, by slicing through the midpoints of six intersecting edges', 'No, cubes can only yield 4-sided cuts', 'Only if the cube is hollow', 'No, never'],
                        'answer': 'Yes, by slicing through the midpoints of six intersecting edges',
                        'hint': 'A plane cutting through 6 consecutive edge midpoints forms a hexagon.'
                    }
                ]
            },
            {
                'title': 'Perspective Projection Quest [Demo Data]',
                'description': 'Interpret complex front, top, and isometric views of multi-tiered structures!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In an architectural blueprint, which drawing shows a building viewed from directly above as if looking down from a cloud?',
                        'options': ['The Plan View (Top View)', 'The Elevation View', 'The Cross-Section', 'The Worm-Eye View'],
                        'answer': 'The Plan View (Top View)',
                        'hint': 'A floor plan or site plan looks straight down from overhead.'
                    },
                    {
                        'text': 'A structure looks like a tall rectangle from the front and a circle from above. What 3D object could this be?',
                        'options': ['A Cylinder', 'A Sphere', 'A Cube', 'A Pyramid'],
                        'answer': 'A Cylinder',
                        'hint': 'A soda can looks rectangular from the side and circular from above.'
                    },
                    {
                        'text': 'If an isometric drawing uses 30-degree grid axes, how are parallel edges in the real 3D object represented?',
                        'options': ['As parallel lines with no vanishing point distortion', 'As converging curved lines', 'As dashed dots', 'As random zig-zags'],
                        'answer': 'As parallel lines with no vanishing point distortion',
                        'hint': 'Isometric projections preserve parallel lines without foreshortening.'
                    }
                ]
            },
            {
                'title': 'Prism Rainbow Quest [Demo Data]',
                'description': 'Explore how sunlight breaks into a dazzling spectrum and identify vibrant secondary hues!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'When light passes through a crystal prism, which colorful arch appears?',
                        'options': ['A Rainbow', 'A Black Shadow', 'A Silver Coin', 'A Brown Rock'],
                        'answer': 'A Rainbow',
                        'hint': 'It appears in the sky after a sun shower!'
                    },
                    {
                        'text': 'Which color do you get when you mix cool blue paint with sunny yellow paint?',
                        'options': ['Green', 'Red', 'Pink', 'Orange'],
                        'answer': 'Green',
                        'hint': 'Think of fresh grass and spring leaves!'
                    },
                    {
                        'text': 'Which shape has no straight sides and rolls smoothly across the floor like a ball?',
                        'options': ['Circle', 'Square', 'Triangle', 'Diamond'],
                        'answer': 'Circle',
                        'hint': 'It is round all the way around!'
                    },
                    {
                        'text': 'Look at the sky during a clear, sunny morning. What color dominates the horizon?',
                        'options': ['Bright Sky Blue', 'Lime Green', 'Jet Black', 'Polka Dot Purple'],
                        'answer': 'Bright Sky Blue',
                        'hint': 'Birds fly through this cheerful color every day!'
                    },
                    {
                        'text': 'If you have a big red square and a tiny red square, how are they the same?',
                        'options': ['They have the same color and 4 sides', 'They have different colors', 'One is round', 'Neither has corners'],
                        'answer': 'They have the same color and 4 sides',
                        'hint': 'Both wear red and both have 4 equal edges!'
                    }
                ]
            },
            {
                'title': 'Symmetry Safari [Demo Data]',
                'description': 'Spot perfect balance and mirror reflection lines across nature and architecture!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'If you fold a picture of a butterfly in half down the middle, what happens to the two wings?',
                        'options': ['They match each other perfectly', 'One is much bigger', 'They change into squares', 'They disappear'],
                        'answer': 'They match each other perfectly',
                        'hint': 'Nature creates mirror images on both sides!'
                    },
                    {
                        'text': 'Which of these capital letters has a vertical line of symmetry down its middle?',
                        'options': ['Letter A', 'Letter F', 'Letter J', 'Letter P'],
                        'answer': 'Letter A',
                        'hint': 'A line straight down the peak splits it into two matching halves.'
                    },
                    {
                        'text': 'How many lines of symmetry does a regular four-sided square have?',
                        'options': ['4 Lines', '1 Line', '2 Lines', '0 Lines'],
                        'answer': '4 Lines',
                        'hint': 'You can fold it vertically, horizontally, and along two diagonals!'
                    },
                    {
                        'text': 'Look in a calm forest pond. Why does the tall pine tree appear upside down in the water?',
                        'options': ['Water reflection acts like a mirror', 'The tree grew downwards', 'The pond painted it', 'The wind blew it'],
                        'answer': 'Water reflection acts like a mirror',
                        'hint': 'Smooth water reflects light symmetrically across the shoreline.'
                    },
                    {
                        'text': 'Which sea creature is famous for five-point radial symmetry branching from its center?',
                        'options': ['Sea Star (Starfish)', 'Eel', 'Flounder', 'Lobster'],
                        'answer': 'Sea Star (Starfish)',
                        'hint': 'It has 5 arms radiating like a glowing night star!'
                    }
                ]
            },
            {
                'title': 'Perspective Architect [Demo Data]',
                'description': 'Visualize 3D structures from top-down, side-elevation, and isometric angles!',
                'difficulty': 'Medium',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'If you look straight down at a solid cylinder from directly above, what 2D shape do you see?',
                        'options': ['Circle', 'Rectangle', 'Triangle', 'Hexagon'],
                        'answer': 'Circle',
                        'hint': 'Looking down into a cup or can reveals its circular rim.'
                    },
                    {
                        'text': 'A pyramid with a square base is viewed directly from the side. What 2D silhouette is visible?',
                        'options': ['Triangle', 'Square', 'Circle', 'Pentagon'],
                        'answer': 'Triangle',
                        'hint': 'The sloping triangular faces meet at the apex point.'
                    },
                    {
                        'text': 'How many flat square faces does a standard solid cube have?',
                        'options': ['6 faces', '4 faces', '8 faces', '12 faces'],
                        'answer': '6 faces',
                        'hint': 'Count top, bottom, front, back, left, and right!'
                    },
                    {
                        'text': 'Two railway tracks look like they meet far in the distance on the horizon. What is this point called in perspective drawing?',
                        'options': ['Vanishing Point', 'Center of Gravity', 'Equator', 'Tangent Line'],
                        'answer': 'Vanishing Point',
                        'hint': 'Parallel lines appear to vanish together at this single spot.'
                    },
                    {
                        'text': 'You build a staircase with toy blocks. Looking from the side, what shape is the outline?',
                        'options': ['Stepped zigzag profile', 'Perfect circle', 'Single flat line', 'Oval curve'],
                        'answer': 'Stepped zigzag profile',
                        'hint': 'Each riser and tread creates an alternating right angle step.'
                    }
                ]
            },
            {
                'title': 'Kaleidoscope Pattern Party [Demo Data]',
                'description': 'Match vibrant stained-glass shapes, spot mirror symmetry, and sort tiny gems in the kaleidoscope studio!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Look at the colorful mosaic! Which friendly shape has 4 equal sides and looks like a wrapped gift box?',
                        'options': ['Square', 'Circle', 'Oval', 'Heart'],
                        'answer': 'Square',
                        'hint': 'Count 4 equal straight edges all the way around!'
                    },
                    {
                        'text': "In the magical garden, a butterfly's left wing has 3 bright blue spots. How many blue spots should its right wing have to match?",
                        'options': ['1 spot', '3 spots', '5 spots', '0 spots'],
                        'answer': '3 spots',
                        'hint': 'Both wings mirror each other like looking into calm water.'
                    },
                    {
                        'text': 'Which friendly shape has no sharp corners at all and rolls smoothly across the play rug like a shiny ball?',
                        'options': ['Triangle', 'Rectangle', 'Circle', 'Square'],
                        'answer': 'Circle',
                        'hint': 'It curves gently round and round with zero pointy edges.'
                    },
                    {
                        'text': 'If you group buttons by size, which button belongs in the tiny critter pile?',
                        'options': ['A giant dinner plate', 'A baby ladybug button', 'A big wagon wheel', 'A huge frisbee'],
                        'answer': 'A baby ladybug button',
                        'hint': "Find the smallest one that would fit easily in a fairy's palm."
                    },
                    {
                        'text': 'What bright color shines through the kaleidoscope when you see fresh summer grass and leafy treetops?',
                        'options': ['Purple', 'Green', 'Orange', 'Grey'],
                        'answer': 'Green',
                        'hint': 'Think of mixing yellow sunshine and blue raindrops!'
                    }
                ]
            },
            {
                'title': 'Mirror Castle Maze [Demo Data]',
                'description': 'Navigate reflections, symmetry lines, and rotating maze pathways through the glittering hall of mirrors!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'You hold a paper crown up to the enchanted mirror. Where does the tall center jewel appear in the reflection?',
                        'options': ['Upside down at the floor', 'Right in the center top', 'Off to the left side', 'Vanished into thin air'],
                        'answer': 'Right in the center top',
                        'hint': 'A reflection mirrors exactly what stands right in front of it.'
                    },
                    {
                        'text': 'Which letter of the alphabet looks exactly the same when viewed in a vertical wall mirror?',
                        'options': ['F', 'L', 'M', 'P'],
                        'answer': 'M',
                        'hint': 'Look for a letter with perfect balance between its left and right sides.'
                    },
                    {
                        'text': 'A crystal arrow points toward the East. If you turn it 90 degrees clockwise, where does it point?',
                        'options': ['North', 'South', 'West', 'Northwest'],
                        'answer': 'South',
                        'hint': "Follow the clock hand moving downward from 3 o'clock to 6 o'clock."
                    },
                    {
                        'text': 'Which shape can you fold right down the middle so both halves match up like fluttering wings?',
                        'options': ['An uneven jagged rock', 'A lopsided squiggle', 'A symmetrical heart', 'A random ink blot'],
                        'answer': 'A symmetrical heart',
                        'hint': 'Look for two identical mirrored halves that fold together evenly.'
                    },
                    {
                        'text': 'In the stained glass hallway, the pattern goes: Blue Diamond, Red Star, Blue Diamond, Red Star, ... What comes next?',
                        'options': ['Green Square', 'Red Star', 'Blue Diamond', 'Yellow Circle'],
                        'answer': 'Blue Diamond',
                        'hint': 'Follow the repeating two-color rhythm of the castle windows!'
                    }
                ]
            },
            {
                'title': 'Isometric Block Builder [Demo Data]',
                'description': 'Build 3D block sculptures, count hidden unit cubes, and match top-down blueprints with side elevations!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'You stack 3 wooden blocks in a vertical column and place 1 block beside the bottom one. How many total blocks are in this L-shaped sculpture?',
                        'options': ['3 blocks', '4 blocks', '5 blocks', '6 blocks'],
                        'answer': '4 blocks',
                        'hint': 'Count the 3 tall blocks in the column plus the 1 base block attached at the bottom.'
                    },
                    {
                        'text': 'Looking directly down from a hot-air balloon onto a pyramid with a square base, what 2D shape do you see on the ground?',
                        'options': ['A circle', 'A star', 'A triangle', 'A square with diagonal lines meeting in the center'],
                        'answer': 'A square with diagonal lines meeting in the center',
                        'hint': 'The square base frames the four triangular faces meeting right at the apex.'
                    },
                    {
                        'text': 'A solid cube is made of 8 smaller unit cubes (2x2x2). If you paint the entire outside blue, how many small cubes have blue paint on 3 faces?',
                        'options': ['0 cubes', '4 cubes', '6 cubes', '8 cubes'],
                        'answer': '8 cubes',
                        'hint': 'Every single one of the 8 small cubes is located at an outer corner of the 2x2x2 block.'
                    },
                    {
                        'text': "You rotate a 3D block letter 'L' 180 degrees flat on the drafting table. Which way does its long vertical spine now point?",
                        'options': ['Upwards', 'Downwards', 'Left', 'Tilted at 45 degrees'],
                        'answer': 'Downwards',
                        'hint': 'A half-turn (180 degrees) completely inverts top to bottom.'
                    },
                    {
                        'text': 'From the front, a sculpture looks like a 3-block tall wall. From the side, it looks like a 1-block thin column. What is the layout of the sculpture?',
                        'options': ['A wide flat square', 'A circular tube', 'A single straight row 3 blocks high and 1 block deep', 'A pyramid shape'],
                        'answer': 'A single straight row 3 blocks high and 1 block deep',
                        'hint': 'The side elevation confirms the structure has a depth of only one unit block.'
                    }
                ]
            },
            {
                'title': 'Optical Matrix Deduction [Demo Data]',
                'description': 'Master 3x3 visual transformation matrices, spatial rotation algorithms, and multi-layered shape transformations!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In a 3x3 visual puzzle, Row 1 has 1 dot, 2 dots, 3 dots. Row 2 has 2 dots, 3 dots, 4 dots. If Row 3 has 3 dots, 4 dots, what comes in the final cell?',
                        'options': ['4 dots', '5 dots', '6 dots', '3 dots'],
                        'answer': '5 dots',
                        'hint': 'Each row increases by +1 moving right, and each column increases by +1 moving down.'
                    },
                    {
                        'text': "A gear wheel has a single gold tooth at the 12 o'clock position. If the gear rotates 270 degrees counter-clockwise, where does the gold tooth land?",
                        'options': ["3 o'clock", "6 o'clock", "9 o'clock", "12 o'clock"],
                        'answer': "3 o'clock",
                        'hint': 'Turning 270 degrees counter-clockwise is equivalent to turning 90 degrees clockwise.'
                    },
                    {
                        'text': 'In an abstract matrix, Layer A (horizontal stripes) combines with Layer B (vertical stripes) using an overlapping rule. What texture does the result create?',
                        'options': ['Solid black', 'A checkered grid', 'Diagonal waves', 'Empty white space'],
                        'answer': 'A checkered grid',
                        'hint': 'Crossed horizontal and vertical parallel lines form a square grid matrix.'
                    },
                    {
                        'text': 'A regular hexagon is sliced by two straight cuts connecting opposite vertices through the center. How many identical equilateral triangles are formed?',
                        'options': ['4 triangles', '5 triangles', '6 triangles', '8 triangles'],
                        'answer': '6 triangles',
                        'hint': 'Three diagonals passing through the center divide a regular hexagon into 6 equilateral wedges.'
                    },
                    {
                        'text': 'A complex visual glyph is reflected across the vertical axis, then reflected across the horizontal axis. This two-step reflection is equivalent to which single transformation?',
                        'options': ['A 90-degree clockwise turn', 'A 180-degree rotation', 'An identity no-change transformation', 'A 45-degree tilt'],
                        'answer': 'A 180-degree rotation',
                        'hint': 'Reflecting across both x and y axes maps coordinate (x, y) to (-x, -y).'
                    }
                ]
            }
        ]
    },

    # =========================================================================
    # 2. LOGIC
    # =========================================================================
    {
        'name': 'Logic',
        'slug': 'logic',
        'icon': '🧩',
        'description': 'Cultivate deductive reasoning, categorization, and problem solving.',
        'activities': [
            # --- Ages 4-6 ---
            {
                'title': 'Animal Friends [Demo Data]',
                'description': 'Help woodland creatures solve playful riddles about habitats, sounds, and cozy homes!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which feathered friend has wings and loves to soar high into the blue sky?',
                        'options': ['Eagle', 'Elephant', 'Whale', 'Turtle'],
                        'answer': 'Eagle',
                        'hint': 'It builds a high nest and flies above the clouds.'
                    },
                    {
                        'text': 'Which cuddly pet purrs softly and says "Meow"?',
                        'options': ['Cat', 'Dog', 'Cow', 'Duck'],
                        'answer': 'Cat',
                        'hint': 'It loves playing with yarn and chasing toy mice.'
                    },
                    {
                        'text': 'Where do silver fish swim, splash, and play all day?',
                        'options': ['In fresh water', 'In the dry desert sand', 'In tree branches', 'Inside clouds'],
                        'answer': 'In fresh water',
                        'hint': 'They breathe with gills under water.'
                    }
                ]
            },
            {
                'title': 'Day and Night [Demo Data]',
                'description': 'Explore sunshine routines, cozy bedtime habits, and weather changes!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'What bright golden light wakes up the world every morning?',
                        'options': ['The Sun', 'The Moon', 'A Flashlight', 'A Streetlamp'],
                        'answer': 'The Sun',
                        'hint': 'It rises in the East and warms the grass.'
                    },
                    {
                        'text': 'Which chilly season brings soft white snow and cozy wool mittens?',
                        'options': ['Winter', 'Summer', 'Spring', 'Autumn'],
                        'answer': 'Winter',
                        'hint': 'It is the coldest time of the year.'
                    },
                    {
                        'text': 'When rain tap-dances on your roof, what pops open to keep you dry outside?',
                        'options': ['An Umbrella', 'Sunglasses', 'A Swimming Mask', 'Sandals'],
                        'answer': 'An Umbrella',
                        'hint': 'You hold its handle over your head.'
                    }
                ]
            },
            {
                'title': 'Who Belongs Where? [Demo Data]',
                'description': 'Match playful animal helpers to their favorite cozy homes and jobs!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'A busy honeybee flew back with sweet nectar. Where is her buzzing home?',
                        'options': ['A Beehive', 'Underground Cave', 'In the ocean', 'On a snowy glacier'],
                        'answer': 'A Beehive',
                        'hint': 'It is filled with golden honeycombs.'
                    },
                    {
                        'text': 'Where does a wise mother bird lay her eggs to keep them safe and warm?',
                        'options': ['In a twiggy Nest', 'In a swimming pool', 'On a highway', 'Inside a backpack'],
                        'answer': 'In a twiggy Nest',
                        'hint': 'She weaves it gently high up in the tree branches.'
                    },
                    {
                        'text': 'Who wears a shiny badge and helps children cross the street safely?',
                        'options': ['School Crossing Guard / Police Officer', 'A Magician', 'A Scuba Diver', 'An Astronaut'],
                        'answer': 'School Crossing Guard / Police Officer',
                        'hint': 'They hold up a bright red STOP sign.'
                    }
                ]
            },
            {
                'title': 'Big & Little Helper [Demo Data]',
                'description': 'Compare sizes, helpers, and simple cause-and-effect puzzles in the garden!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'If you plant a tiny sunflower seed in warm soil and water it, what happens?',
                        'options': ['It sprouts and grows into a tall flower', 'It turns into a rock', 'It melts into water', 'It flies into outer space'],
                        'answer': 'It sprouts and grows into a tall flower',
                        'hint': 'Seeds drink water and reach up toward the sun.'
                    },
                    {
                        'text': 'Who is bigger: a playful little mouse or a friendly giant elephant?',
                        'options': ['The Elephant', 'The Mouse', 'They are the same size', 'Neither'],
                        'answer': 'The Elephant',
                        'hint': 'One has a long swinging trunk and huge ears!'
                    },
                    {
                        'text': 'If you turn on the garden hose tap, what comes splashing out?',
                        'options': ['Water', 'Orange juice', 'Sand', 'Snowflakes'],
                        'answer': 'Water',
                        'hint': 'It helps the thirsty green grass grow.'
                    }
                ]
            },

            # --- Ages 6-9 ---
            {
                'title': 'Sequence Detective [Demo Data]',
                'description': 'Put daily adventures in the right order and unravel cause-and-effect mysteries!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'What is the very first step in baking delicious cookies?',
                        'options': ['Mix the ingredients and dough', 'Eat the warm cookies', 'Pack them in a box', 'Wash the empty plates'],
                        'answer': 'Mix the ingredients and dough',
                        'hint': 'You must prepare the batter before baking.'
                    },
                    {
                        'text': 'Cat is to Kitten as Dog is to ___?',
                        'options': ['Puppy', 'Cub', 'Calf', 'Foal'],
                        'answer': 'Puppy',
                        'hint': 'What is a cute baby dog called?'
                    },
                    {
                        'text': 'You drop an ice cube on a warm sidewalk on a hot summer day. What happens next?',
                        'options': ['It melts into a puddle of water', 'It turns into wood', 'It gets colder and colder', 'It bounces like a ball'],
                        'answer': 'It melts into a puddle of water',
                        'hint': 'Heat warms frozen ice and turns it to liquid.'
                    }
                ]
            },
            {
                'title': 'Silly Rule Detective [Demo Data]',
                'description': 'Discover secret playground rules and spot which playful clue unlocks the door!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Rule: Only animals with wings may enter the treehouse club. Who is allowed in?',
                        'options': ['Robin the Bird', 'Leo the Lion', 'Bella the Bunny', 'Oliver the Otter'],
                        'answer': 'Robin the Bird',
                        'hint': 'Check which animal has feathered wings to fly up.'
                    },
                    {
                        'text': 'Secret Code: Every word in the treasure chest must start with the letter "S". Which item belongs?',
                        'options': ['Star', 'Moon', 'Planet', 'Comet'],
                        'answer': 'Star',
                        'hint': 'Sound out the first letter: "sss".'
                    },
                    {
                        'text': 'If all tigers are felines, and all felines have whiskers, do tigers have whiskers?',
                        'options': ['Yes, definitely!', 'No, never', 'Only on Tuesdays', 'Cannot be determined'],
                        'answer': 'Yes, definitely!',
                        'hint': 'Follow the logic chain: Tiger -> Feline -> Whiskers.'
                    }
                ]
            },
            {
                'title': 'Cause & Effect Carnival [Demo Data]',
                'description': 'Press carnival buttons, roll wooden marbles, and predict the chain reaction!',
                'difficulty': 'Medium',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'In a domino rally, if marble #1 knocks down domino #1, what happens to domino #2 right next to it?',
                        'options': ['It gets pushed over by domino #1', 'It jumps into the air', 'It stands still forever', 'It turns into water'],
                        'answer': 'It gets pushed over by domino #1',
                        'hint': 'The chain reaction passes kinetic energy along the line.'
                    },
                    {
                        'text': 'If you flip the wall light switch into the ON position, what happens in a dark room?',
                        'options': ['The light bulb shines brightly', 'The room gets darker', 'Music starts playing', 'The windows open'],
                        'answer': 'The light bulb shines brightly',
                        'hint': 'The switch connects the electric circuit.'
                    },
                    {
                        'text': 'Liam forgot his raincoat on a stormy day. When he arrives at school, how will his jacket feel?',
                        'options': ['Damp and wet from the rain', 'Completely dry', 'Covered in desert sand', 'Toasty warm like toast'],
                        'answer': 'Damp and wet from the rain',
                        'hint': 'Rain without protection makes clothes wet.'
                    }
                ]
            },
            {
                'title': 'Mystery Clue Hunt [Demo Data]',
                'description': 'Piece together 2 or 3 clever clues to discover which mystery pet is hiding behind the door!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Clue 1: I have long floppy ears. Clue 2: I love hopping through grassy fields and munching crunchy carrots. Who am I?',
                        'options': ['A Bunny Rabbit', 'A Goldfish', 'A Parrot', 'A Turtle'],
                        'answer': 'A Bunny Rabbit',
                        'hint': 'Watch it hop with its twitchy little nose!'
                    },
                    {
                        'text': 'Clue 1: I live in water. Clue 2: I carry a hard protective shell on my back and walk slowly on land. Who am I?',
                        'options': ['A Turtle', 'A Dolphin', 'A Cheetah', 'A Monkey'],
                        'answer': 'A Turtle',
                        'hint': 'It can pull its head inside its shell.'
                    },
                    {
                        'text': 'Clue 1: I have black and yellow stripes. Clue 2: I make honey and buzz in gardens. Who am I?',
                        'options': ['A Bumblebee', 'A Butterfly', 'A Dragonfly', 'A Beetle'],
                        'answer': 'A Bumblebee',
                        'hint': 'It buzzes from blossom to blossom.'
                    }
                ]
            },

            # --- Ages 9-12 ---
            {
                'title': 'Problem Solver [Demo Data]',
                'description': 'Sharpen deductive logic skills with relational puzzles and deduction chains!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Anna is taller than Ben. Ben is taller than Chris. Who is the tallest of all three?',
                        'options': ['Anna', 'Ben', 'Chris', 'All are the same height'],
                        'answer': 'Anna',
                        'hint': 'Anna is taller than Ben, who is taller than Chris.'
                    },
                    {
                        'text': 'All parrots have feathers. Kiwi is a parrot. Does Kiwi have feathers?',
                        'options': ['Yes, definitely', 'No', 'Only when flying', 'Cannot tell'],
                        'answer': 'Yes, definitely',
                        'hint': 'Kiwi belongs to the group of parrots, so the rule applies.'
                    },
                    {
                        'text': 'If today is Wednesday, what day of the week was it exactly 3 days ago?',
                        'options': ['Sunday', 'Monday', 'Tuesday', 'Thursday'],
                        'answer': 'Sunday',
                        'hint': 'Count backwards: Tuesday (1), Monday (2), Sunday (3).'
                    }
                ]
            },
            {
                'title': 'Mini Sudoku 4x4 [Demo Data]',
                'description': 'Fill in the 4x4 number puzzle grid so numbers 1 to 4 appear once in every row, column, and box!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'In row 1 of a 4x4 grid, the numbers are: 1, 2, __, 4. Which missing number goes in the blank?',
                        'options': ['3', '1', '2', '5'],
                        'answer': '3',
                        'hint': 'Every number from 1 to 4 must appear exactly once.'
                    },
                    {
                        'text': 'In a 2x2 sub-box, you already have: 2, 3, 4. What number must fill the final fourth square?',
                        'options': ['1', '2', '3', '0'],
                        'answer': '1',
                        'hint': 'Check which digit from 1, 2, 3, 4 is missing.'
                    },
                    {
                        'text': 'Column 2 has: 4, 1, 3, __. What number completes the column?',
                        'options': ['2', '1', '3', '4'],
                        'answer': '2',
                        'hint': 'The remaining number is 2.'
                    }
                ]
            },
            {
                'title': 'Truth & Trickster Riddles [Demo Data]',
                'description': 'Outsmart playful tricksters on Riddle Island who always tell truths or playful fibs!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Guide Theo always tells the truth. He points to door #1 and says: "Behind this door is a friendly puppy." What is behind door #1?',
                        'options': ['A friendly puppy', 'A roaring lion', 'Empty space', 'A brick wall'],
                        'answer': 'A friendly puppy',
                        'hint': 'Theo always speaks the pure truth.'
                    },
                    {
                        'text': 'Trickster Toby always tells the opposite of the truth. He says: "It is raining outside right now!" Is it raining?',
                        'options': ['No, it is not raining', 'Yes, it is pouring', 'It is snowing', 'Cannot tell'],
                        'answer': 'No, it is not raining',
                        'hint': 'If Toby says it is raining, the real condition is the opposite.'
                    },
                    {
                        'text': 'Two guards stand at a fork in the road. One always lies, one always tells truth. What single question reveals the safe path?',
                        'options': ['"Which road would the other guard say is safe?" (then take opposite)', '"What color is your hat?"', '"Do you like pizza?"', '"Are you asleep?"'],
                        'answer': '"Which road would the other guard say is safe?" (then take opposite)',
                        'hint': 'Asking about the other guard forces a lie regardless of who you ask!'
                    }
                ]
            },
            {
                'title': 'Logical Flow Master [Demo Data]',
                'description': 'Follow conditional computer code rules: IF this happens, THEN do that, ELSE take the shortcut!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Rule: IF energy > 50 THEN run_forward() ELSE rest_under_tree(). Your energy is 75. What does the robot do?',
                        'options': ['run_forward()', 'rest_under_tree()', 'power_off()', 'jump_backward()'],
                        'answer': 'run_forward()',
                        'hint': '75 is greater than 50, so the condition is true.'
                    },
                    {
                        'text': 'Rule: IF has_key == True AND door_locked == True THEN unlock_door(). You have no key (has_key = False). Can you unlock the door?',
                        'options': ['No, both conditions must be true for AND', 'Yes, easily', 'Only halfway', 'The door vanishes'],
                        'answer': 'No, both conditions must be true for AND',
                        'hint': 'An AND condition requires both sides to be true.'
                    },
                    {
                        'text': 'What is the outcome of: IF score >= 10 OR stars >= 3 THEN win_trophy()? Your score is 5, but you have 3 stars.',
                        'options': ['win_trophy() (OR requires only one condition to be true)', 'No trophy', 'Game over', 'Lose 5 points'],
                        'answer': 'win_trophy() (OR requires only one condition to be true)',
                        'hint': 'An OR rule succeeds if at least one part is satisfied.'
                    }
                ]
            },

            # --- Ages 12-14 ---
            {
                'title': 'Deductive Logic Grid [Demo Data]',
                'description': 'Crack multi-variable logic grids using clues to match friends, pets, and favorite hobbies!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Clue 1: Maya owns the cat. Clue 2: The person who plays soccer owns a dog. Clue 3: Liam plays tennis. Does Maya play soccer?',
                        'options': ['No, because the soccer player owns a dog, and Maya owns the cat', 'Yes, Maya plays soccer', 'Maya has no pet', 'Cannot be deduced'],
                        'answer': 'No, because the soccer player owns a dog, and Maya owns the cat',
                        'hint': 'Match the pet constraints: Cat owner != Dog owner (soccer player).'
                    },
                    {
                        'text': 'Four houses are in a row: Red, Blue, Green, Yellow. Green is to the left of Blue. Red is between Yellow and Green. Which house is furthest left?',
                        'options': ['Yellow', 'Green', 'Red', 'Blue'],
                        'answer': 'Yellow',
                        'hint': 'Arrange the line: Yellow - Red - Green - Blue.'
                    },
                    {
                        'text': 'Three racers finish: Alex, Bea, Carlos. Alex did not finish last. Bea finished immediately after Carlos. Who won 1st place?',
                        'options': ['Carlos (Carlos 1st, Bea 2nd, Alex 3rd is impossible since Alex != last; so Alex 1st, Carlos 2nd, Bea 3rd)', 'Bea', 'Nobody', 'All tied'],
                        'answer': 'Carlos (Carlos 1st, Bea 2nd, Alex 3rd is impossible since Alex != last; so Alex 1st, Carlos 2nd, Bea 3rd)',
                        'hint': 'If Alex cannot be last, Bea is after Carlos, test the order: Carlos, Bea, Alex or Alex, Carlos, Bea.'
                    }
                ]
            },
            {
                'title': 'Syllogism Explorer [Demo Data]',
                'description': 'Examine formal logic arguments, evaluate validity, and expose tricky fallacies!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Premise 1: All metals conduct electricity. Premise 2: Copper is a metal. What logically follows with 100% certainty?',
                        'options': ['Copper conducts electricity', 'Copper is expensive', 'All conductors are copper', 'No metals are conductors'],
                        'answer': 'Copper conducts electricity',
                        'hint': 'This is a classic valid deductive syllogism (Modus Ponens).'
                    },
                    {
                        'text': 'Premise 1: Some reptiles can swim. Premise 2: All snakes are reptiles. Does it follow that ALL snakes can swim?',
                        'options': ['No, "some reptiles" does not guarantee all reptiles or all snakes swim', 'Yes, all snakes swim', 'No snakes can swim', 'Reptiles are fish'],
                        'answer': 'No, "some reptiles" does not guarantee all reptiles or all snakes swim',
                        'hint': 'Beware the quantifier "some" — it does not distribute to all subsets.'
                    },
                    {
                        'text': '"If it is raining, the grass is wet. The grass is wet. Therefore, it MUST be raining." Is this deduction valid?',
                        'options': ['No, this is the fallacy of affirming the consequent (sprinklers could wet the grass)', 'Yes, completely valid', 'Only at night', 'Yes, rain is the only liquid'],
                        'answer': 'No, this is the fallacy of affirming the consequent (sprinklers could wet the grass)',
                        'hint': 'The grass could be wet for another reason, like a sprinkler or morning dew.'
                    }
                ]
            },
            {
                'title': 'Paradox & Fallacy Sleuth [Demo Data]',
                'description': 'Explore famous paradoxes (Zeno, Liar) and uncover logical sleights of hand!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Consider the sentence: "This statement is false." What happens if you assume the statement is true?',
                        'options': ['It creates a paradox (if true, then it is false; if false, then it is true)', 'It proves it is 100% true', 'It has no meaning', 'It equals zero'],
                        'answer': 'It creates a paradox (if true, then it is false; if false, then it is true)',
                        'hint': 'This is the ancient Epimenides Liar Paradox.'
                    },
                    {
                        'text': 'In an argument, someone attacks the speaker personally instead of addressing their evidence. What fallacy is this?',
                        'options': ['Ad Hominem', 'Straw Man', 'Circular Reasoning', 'Slippery Slope'],
                        'answer': 'Ad Hominem',
                        'hint': 'Latin for "to the person" — attacking the person rather than their claim.'
                    },
                    {
                        'text': '"Every piece of this bicycle is lightweight, therefore the assembled bicycle weighs almost zero." What fallacy is committed?',
                        'options': ['Fallacy of Composition (assuming what is true of parts is true of the whole)', 'Hasty Generalization', 'Bandwagon Fallacy', 'False Dilemma'],
                        'answer': 'Fallacy of Composition (assuming what is true of parts is true of the whole)',
                        'hint': 'Adding together many lightweight parts still creates substantial total mass.'
                    }
                ]
            },
            {
                'title': 'Multi-Constraint Escape [Demo Data]',
                'description': 'Solve complex resource management and scheduling puzzle challenges to unlock the escape pod!',
                'difficulty': 'Advanced',
                'duration': 10,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'You have a 3-liter jug and a 5-liter jug, with unlimited water. How can you measure exactly 4 liters?',
                        'options': ['Fill 5L, pour into 3L (leaves 2L in 5L). Empty 3L, pour 2L into 3L. Fill 5L again, pour into 3L until full (+1L) leaving 4L in 5L jug!', 'Fill 3L twice', 'Drink 1 liter', 'Guess the halfway point'],
                        'answer': 'Fill 5L, pour into 3L (leaves 2L in 5L). Empty 3L, pour 2L into 3L. Fill 5L again, pour into 3L until full (+1L) leaving 4L in 5L jug!',
                        'hint': 'Track the exact steps in the classic water jug problem.'
                    },
                    {
                        'text': 'A farmer must cross a river with a wolf, a goat, and cabbage. The boat carries only the farmer and one item. What must cross first?',
                        'options': ['The Goat (leaving wolf and cabbage safely together)', 'The Wolf', 'The Cabbage', 'The Farmer alone'],
                        'answer': 'The Goat (leaving wolf and cabbage safely together)',
                        'hint': 'Wolves do not eat cabbage, but wolves eat goats and goats eat cabbage!'
                    },
                    {
                        'text': 'Task A takes 2 hrs, Task B takes 3 hrs, Task C takes 1 hr. Task C depends on both A and B finishing. What is the minimum project completion time?',
                        'options': ['4 hours (A and B run in parallel for 3 hrs, then C takes 1 hr: 3 + 1 = 4)', '6 hours', '2 hours', '5 hours'],
                        'answer': '4 hours (A and B run in parallel for 3 hrs, then C takes 1 hr: 3 + 1 = 4)',
                        'hint': 'Tasks without mutual dependencies can run simultaneously on the critical path.'
                    }
                ]
            },
            {
                'title': 'Barnyard Cause and Effect [Demo Data]',
                'description': 'Learn how actions lead to reactions across a cheerful countryside farm!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'When the farmer plants a sunflower seed in moist soil and the sun shines, what happens?',
                        'options': ['A sprout grows into a flower', 'It turns into an ice cube', 'It floats into the sky', 'Nothing ever happens'],
                        'answer': 'A sprout grows into a flower',
                        'hint': 'Seeds need water and sunlight to sprout and grow!'
                    },
                    {
                        'text': 'If heavy raindrops fall from dark clouds onto the barnyard dirt, what forms on the ground?',
                        'options': ['Muddy puddles', 'Dry sand dunes', 'Crisp snowflakes', 'Hot soup'],
                        'answer': 'Muddy puddles',
                        'hint': 'Water mixes with earth to make squishy mud!'
                    },
                    {
                        'text': 'The rooster crows loudly at dawn as the sun peaks over the hills. What time of day is it?',
                        'options': ['Morning', 'Midnight', 'Dinner time', 'Bedtime'],
                        'answer': 'Morning',
                        'hint': 'The sun is just rising to start a brand-new day!'
                    },
                    {
                        'text': 'If the stable gate is left wide open, what might the curious pony do?',
                        'options': ['Trot out into the green meadow', 'Fly like an airplane', 'Go to sleep instantly', 'Turn purple'],
                        'answer': 'Trot out into the green meadow',
                        'hint': 'Animals like to explore open spaces when doors are unlocked!'
                    },
                    {
                        'text': 'Why does the woolly sheep feel cooler in the summertime after shearing?',
                        'options': ['Her heavy winter coat was trimmed off', 'She drank hot tea', 'She put on a sweater', 'She stayed inside a cave'],
                        'answer': 'Her heavy winter coat was trimmed off',
                        'hint': 'Removing thick wool lets the refreshing summer breeze reach her skin!'
                    }
                ]
            },
            {
                'title': 'Secret Agent Pathway [Demo Data]',
                'description': 'Follow rules of deduction to navigate maze gates and crack security codes!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Rule: The blue door opens ONLY if the green lever is pulled AND the red key is turned. The green lever is pulled, but the red key is missing. Does the door open?',
                        'options': ['No, both conditions are required', 'Yes, one is enough', 'Yes, the door opens automatically', 'Only at midnight'],
                        'answer': 'No, both conditions are required',
                        'hint': 'The word "AND" means every required condition must be met.'
                    },
                    {
                        'text': 'Code Clue: The security passcode is an EVEN number greater than 14 and less than 18. What is it?',
                        'options': ['16', '15', '17', '19'],
                        'answer': '16',
                        'hint': '15 and 17 are odd numbers; which even number sits between 14 and 18?'
                    },
                    {
                        'text': 'Deduction: Agent Nova wears either brown boots or black shoes. Today she is NOT wearing black shoes. What is on her feet?',
                        'options': ['Brown boots', 'Running sneakers', 'Bare feet', 'Yellow flippers'],
                        'answer': 'Brown boots',
                        'hint': 'If there are only two choices and one is ruled out, the other must be true!'
                    },
                    {
                        'text': 'Three boxes: Gold, Silver, Bronze. The microchip is NOT in Gold. It is NOT in Bronze. Where must it be?',
                        'options': ['Silver Box', 'Gold Box', 'Bronze Box', 'Under the floor'],
                        'answer': 'Silver Box',
                        'hint': 'Eliminate the two impossible locations to find the only one remaining.'
                    },
                    {
                        'text': 'If all secret agents carry badges, and Leo is a secret agent, what can we logically conclude?',
                        'options': ['Leo carries a badge', 'Leo drives a helicopter', 'Leo has two badges', 'Leo lost his badge'],
                        'answer': 'Leo carries a badge',
                        'hint': 'Since Leo belongs to the group, the rule applies to him directly.'
                    }
                ]
            },
            {
                'title': 'Algorithmic Circuit Builder [Demo Data]',
                'description': 'Analyze boolean logic gates (AND, OR, NOT, XOR) and step-by-step conditional algorithms!',
                'difficulty': 'Advanced',
                'duration': 10,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In boolean logic, an XOR (Exclusive OR) gate outputs TRUE under which specific condition?',
                        'options': ['When exactly one input is TRUE and the other is FALSE', 'When both inputs are TRUE', 'When both inputs are FALSE', 'Always under any condition'],
                        'answer': 'When exactly one input is TRUE and the other is FALSE',
                        'hint': 'Exclusive OR requires one or the other, but explicitly NOT both.'
                    },
                    {
                        'text': 'Evaluate this logical expression: (TRUE OR FALSE) AND (NOT FALSE). What is the final result?',
                        'options': ['TRUE', 'FALSE', 'Undefined', 'Null'],
                        'answer': 'TRUE',
                        'hint': '(TRUE OR FALSE) evaluates to TRUE, and (NOT FALSE) evaluates to TRUE. TRUE AND TRUE is TRUE.'
                    },
                    {
                        'text': 'An algorithm checks: "IF temperature > 30 AND humidity > 80 THEN trigger cooling ELSE standby". If temperature is 32 and humidity is 70, what action occurs?',
                        'options': ['Standby', 'Trigger cooling', 'System shutdown', 'Trigger alarm'],
                        'answer': 'Standby',
                        'hint': 'Humidity is 70, which is not > 80. The AND condition fails, so it takes the ELSE branch.'
                    },
                    {
                        'text': 'Which problem-solving strategy systematically breaks a complex problem into smaller subproblems of the same type?',
                        'options': ['Divide and Conquer', 'Random Brute Force', 'Infinite Looping', 'Superficial Guessing'],
                        'answer': 'Divide and Conquer',
                        'hint': 'Commonly used in merge sort, binary search, and recursive algorithms.'
                    },
                    {
                        'text': 'Premise 1: If it rains, the pitch is slippery. Premise 2: If the pitch is slippery, the match is postponed. Fact: It rained. What follows?',
                        'options': ['The match is postponed', 'The match proceeds on schedule', 'It did not rain', 'The pitch is dry'],
                        'answer': 'The match is postponed',
                        'hint': 'Apply hypothetical syllogism: A -> B and B -> C, therefore A -> C.'
                    }
                ]
            },
            {
                'title': 'Animal Habitat Sort [Demo Data]',
                'description': 'Sort woodland creatures, ocean divers, and sky soarers into their natural homes using simple logic rules!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Dolphin Dana loves to swim and splash in salty waves. Where is Dana natural home?',
                        'options': ['The Ocean', 'A Tree House', 'A Desert Sand Dune', 'A Fluffy Cloud'],
                        'answer': 'The Ocean',
                        'hint': 'Look for cool blue water with coral reefs and schools of fish.'
                    },
                    {
                        'text': 'Which of these fluffy forest friends sleeps in a cozy tree hollow during chilly days?',
                        'options': ['A Goldfish', 'An Owl', 'A Shark', 'A Crab'],
                        'answer': 'An Owl',
                        'hint': 'This wise bird has feathers and calls out at twilight.'
                    },
                    {
                        'text': 'Three animal friends are waiting in line: Bunny is first, Turtle is second, Bear is third. Who is standing right in the middle?',
                        'options': ['Bunny', 'Turtle', 'Bear', 'Fox'],
                        'answer': 'Turtle',
                        'hint': 'The second friend stands between the first and the third.'
                    },
                    {
                        'text': 'If all birds have wings, and Pip is a little bluebird, what special feature does Pip definitely have?',
                        'options': ['Fins', 'Wings', 'A Turtle shell', 'Antlers'],
                        'answer': 'Wings',
                        'hint': 'Remember the rule: every single bird has wings!'
                    },
                    {
                        'text': 'Which item does NOT belong in a snowy winter sledding backpack?',
                        'options': ['Warm woolen mittens', 'A fuzzy winter beanie', 'A thick snow jacket', 'A pair of swimming goggles'],
                        'answer': 'A pair of swimming goggles',
                        'hint': 'Pick the item you wear to a sunny swimming pool, not a snowy hill.'
                    }
                ]
            },
            {
                'title': 'Detective Clue Trail [Demo Data]',
                'description': 'Follow mysterious tracks, discover the odd one out, and deduce the secret password of the detective clubhouse!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Detective Fox inspects 4 prints on the forest trail. Which print does NOT belong with the others?',
                        'options': ['Four-toed paw print', 'Three-toed paw print', 'Five-toed paw print', 'A round bicycle tire track'],
                        'answer': 'A round bicycle tire track',
                        'hint': 'Spot the mechanical rubber wheel track among animal paw prints.'
                    },
                    {
                        'text': 'Clue 1: The mystery fruit is yellow. Clue 2: Monkeys love to peel it before snack time. What is the mystery fruit?',
                        'options': ['Strawberry', 'Lemon', 'Banana', 'Blueberry'],
                        'answer': 'Banana',
                        'hint': 'It grows in bunches on tall tropical plants and has a curved shape.'
                    },
                    {
                        'text': 'Rule of the Secret Door: Only passwords with exactly 4 letters will unlock it. Which word opens the clubhouse door?',
                        'options': ['KEY', 'OPEN', 'CLUE', 'TREASURE'],
                        'answer': 'OPEN',
                        'hint': 'Count the letters carefully: O-P-E-N has exactly 4 letters.'
                    },
                    {
                        'text': 'Maya is older than Ben. Ben is older than Chloe. Who is the youngest member of the detective team?',
                        'options': ['Maya', 'Ben', 'Chloe', 'They are all the same age'],
                        'answer': 'Chloe',
                        'hint': 'Arrange the ladder from oldest to youngest: Maya -> Ben -> Chloe.'
                    },
                    {
                        'text': 'If red gemstones are worth more than blue crystals, and blue crystals are worth more than green stones, which item has the highest value?',
                        'options': ['Green stone', 'Blue crystal', 'Red gemstone', 'Yellow pebble'],
                        'answer': 'Red gemstone',
                        'hint': 'The red gemstone sits at the very peak of the value ladder.'
                    }
                ]
            },
            {
                'title': 'Island Logic Grid [Demo Data]',
                'description': 'Solve deductive constraint matrices, rank island explorers, and unlock ancient treasure chests using elimination logic!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Four crew members wear Red, Blue, Green, or Yellow caps. The First Mate wears Blue. The Captain wears Green. The Cook does not wear Red. What color cap does the Cook wear?',
                        'options': ['Red', 'Yellow', 'Blue', 'Green'],
                        'answer': 'Yellow',
                        'hint': 'Blue and Green are already taken. Since the Cook cannot wear Red, Yellow is the only option left.'
                    },
                    {
                        'text': 'In a relay race across Treasure Island, Zara finished before Leo, but after Max. Sam finished after Leo. Who won first place?',
                        'options': ['Max', 'Zara', 'Leo', 'Sam'],
                        'answer': 'Max',
                        'hint': 'Order the finishers from first to last: Max -> Zara -> Leo -> Sam.'
                    },
                    {
                        'text': 'A locked vault requires a 3-digit combination: Digit 1 is an even number greater than 6 (8). Digit 2 is half of Digit 1 (4). Digit 3 is the sum of 1 and 2 (3). What is the code?',
                        'options': ['8-4-3', '6-3-2', '8-2-3', '4-2-1'],
                        'answer': '8-4-3',
                        'hint': 'The single-digit even number greater than 6 is 8. Half of 8 is 4. 1 + 2 is 3.'
                    },
                    {
                        'text': 'Three chests (Gold, Silver, Bronze) sit on a table. The Gold chest is immediately to the left of Silver. Bronze is not on the far left. What is the order from left to right?',
                        'options': ['Bronze, Gold, Silver', 'Gold, Silver, Bronze', 'Silver, Gold, Bronze', 'Bronze, Silver, Gold'],
                        'answer': 'Gold, Silver, Bronze',
                        'hint': 'Gold and Silver must stay together with Gold on the left, placing Bronze at the right end.'
                    },
                    {
                        'text': 'Logical Clue: Either the island compass is broken OR the wind is blowing North. We have proven that the compass works perfectly. What must be true?',
                        'options': ['The wind is blowing South', 'The compass is broken', 'The wind is blowing North', 'Nothing can be determined'],
                        'answer': 'The wind is blowing North',
                        'hint': 'In an "A or B" statement, if option A is proven false, option B must be true.'
                    }
                ]
            },
            {
                'title': 'Cryptic Truth-Seeker Realm [Demo Data]',
                'description': 'Master Knights and Knaves paradoxes, conditional Modus Tollens deductions, and complex multi-variable syllogisms!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': "On the Isle of Logic, Knights always tell the truth and Knaves always lie. Inhabitant X announces: 'Both of us are Knaves.' What can you logically deduce about Inhabitant X?",
                        'options': ['Inhabitant X is a Knight', 'Inhabitant X is a Knave', 'Inhabitant X is a neutral visitor', 'Nothing can be proven'],
                        'answer': 'Inhabitant X is a Knave',
                        'hint': 'A Knight could never claim to be a Knave (that would be a lie). Therefore, the speaker must be lying and is a Knave.'
                    },
                    {
                        'text': 'Premise 1: All cryptographers enjoy logic puzzles. Premise 2: Anyone who enjoys logic puzzles appreciates strategy games. What conclusion is logically guaranteed?',
                        'options': ['All cryptographers appreciate strategy games', 'All strategy game players are cryptographers', 'Some cryptographers dislike games', 'Only cryptographers play puzzles'],
                        'answer': 'All cryptographers appreciate strategy games',
                        'hint': 'Chain the deductive premises: Cryptographer -> Enjoys puzzles -> Appreciates strategy games.'
                    },
                    {
                        'text': 'Conditional Rule: If the drawbridge is lowered, the harbor beacon is lit. The harbor beacon is currently UNLIT. What follows logically?',
                        'options': ['The drawbridge is lowered', 'The drawbridge is not lowered', 'A storm is coming', 'The beacon bulb is burnt out'],
                        'answer': 'The drawbridge is not lowered',
                        'hint': 'Apply Modus Tollens: If P implies Q, and Q is false, then P must be false.'
                    },
                    {
                        'text': 'Four students (Alex, Blair, Casey, Devon) ran a marathon: Blair finished ahead of Casey. Alex finished ahead of Blair. Devon finished behind Casey. Who earned 3rd place?',
                        'options': ['Alex', 'Blair', 'Casey', 'Devon'],
                        'answer': 'Casey',
                        'hint': 'Order from first to fourth: Alex (1st), Blair (2nd), Casey (3rd), Devon (4th).'
                    },
                    {
                        'text': 'A digital security circuit outputs TRUE if and only if Input A and Input B have DIFFERENT binary values. What type of logic gate is this?',
                        'options': ['AND Gate', 'OR Gate', 'XOR (Exclusive OR) Gate', 'NOT Gate'],
                        'answer': 'XOR (Exclusive OR) Gate',
                        'hint': 'Exclusive OR outputs true when inputs are mismatched (one True, one False).'
                    }
                ]
            }
        ]
    },

    # =========================================================================
    # 3. NUMBERS
    # =========================================================================
    {
        'name': 'Numbers',
        'slug': 'numbers',
        'icon': '🔢',
        'description': 'Master counting, basic arithmetic, numerical comparisons, and quantities.',
        'activities': [
            # --- Ages 4-6 ---
            {
                'title': 'Count the Items [Demo Data]',
                'description': 'Count cheerful apples, smiling stars, and friendly kittens on the screen!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'How many fingers do you have on one hand (give a high five!)?',
                        'options': ['5', '3', '4', '10'],
                        'answer': '5',
                        'hint': 'Count thumb, index, middle, ring, pinky: 1, 2, 3, 4, 5!'
                    },
                    {
                        'text': 'What number comes directly after 2 when counting?',
                        'options': ['3', '1', '4', '5'],
                        'answer': '3',
                        'hint': '1, 2, ... what comes next?'
                    },
                    {
                        'text': 'Look at these juicy apples: 🍎 🍎. How many apples are there?',
                        'options': ['2', '1', '3', '4'],
                        'answer': '2',
                        'hint': 'Count one, two!'
                    }
                ]
            },
            {
                'title': 'Number Hopper [Demo Data]',
                'description': 'Help the frog hop along the number lily pads from 1 to 10!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Froggy is on lily pad 4. He takes 1 big forward hop. Which lily pad does he land on?',
                        'options': ['5', '3', '6', '7'],
                        'answer': '5',
                        'hint': 'Add 1 to 4: four plus one equals five.'
                    },
                    {
                        'text': 'Which number looks like a round donut or a smooth wheel?',
                        'options': ['0', '1', '4', '7'],
                        'answer': '0',
                        'hint': 'It is completely round with no corners.'
                    },
                    {
                        'text': 'Count the friendly ducklings: 🦆 🦆 🦆. How many ducklings are swimming?',
                        'options': ['3', '2', '4', '1'],
                        'answer': '3',
                        'hint': 'One, two, three quackers!'
                    }
                ]
            },
            {
                'title': 'Finger Tap Counting [Demo Data]',
                'description': 'Tap along to gentle rhythms and count pairs of shoes, eyes, and mittens!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'How many eyes do you have on your face to see the world?',
                        'options': ['2', '1', '3', '4'],
                        'answer': '2',
                        'hint': 'Wink your left eye, then your right eye!'
                    },
                    {
                        'text': 'If you have 3 shiny stickers and someone gives you 1 more, how many stickers do you have in total?',
                        'options': ['4', '2', '5', '3'],
                        'answer': '4',
                        'hint': 'Count up from 3: 3... 4!'
                    },
                    {
                        'text': 'Which number comes right before 6 when we count?',
                        'options': ['5', '7', '4', '8'],
                        'answer': '5',
                        'hint': '1, 2, 3, 4, __, 6.'
                    }
                ]
            },
            {
                'title': 'More or Less Playground [Demo Data]',
                'description': 'Compare baskets of colorful balloons and find which group has more treats!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Basket A has 5 red balloons: 🎈🎈🎈🎈🎈. Basket B has 2 blue balloons: 🎈🎈. Which basket has MORE balloons?',
                        'options': ['Basket A (5 balloons)', 'Basket B (2 balloons)', 'Both are equal', 'Neither has any'],
                        'answer': 'Basket A (5 balloons)',
                        'hint': '5 is a bigger number than 2.'
                    },
                    {
                        'text': 'Which number is smaller: 1 or 8?',
                        'options': ['1', '8', 'They are the same', 'Zero'],
                        'answer': '1',
                        'hint': '1 is just a single item; 8 is a whole bunch.'
                    },
                    {
                        'text': 'You have 2 hands and 2 feet. Are your hands and feet equal in number?',
                        'options': ['Yes, 2 equals 2!', 'No, hands are more', 'No, feet are more', 'Cannot tell'],
                        'answer': 'Yes, 2 equals 2!',
                        'hint': 'Both counts are exactly the same: 2.'
                    }
                ]
            },

            # --- Ages 6-9 ---
            {
                'title': 'Addition Journey [Demo Data]',
                'description': 'Solve cheerful addition equations and jump along the enchanted rainbow path!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'What is 4 + 3?',
                        'options': ['7', '6', '8', '9'],
                        'answer': '7',
                        'hint': 'Start at 4 and count up three: 5, 6, 7!'
                    },
                    {
                        'text': 'What is 10 - 4?',
                        'options': ['6', '5', '7', '14'],
                        'answer': '6',
                        'hint': 'Think: what number plus 4 equals 10?'
                    },
                    {
                        'text': 'If you have 5 golden coins and discover 5 more in a chest, how many coins do you hold?',
                        'options': ['10', '9', '11', '15'],
                        'answer': '10',
                        'hint': '5 + 5 is a favorite double!'
                    }
                ]
            },
            {
                'title': 'Number Pattern Quest [Demo Data]',
                'description': 'Skip count by 2s, 5s, and 10s to unlock the wizard’s treasure chests!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Count by 2s: 2, 4, 6, 8, ___. What number comes next?',
                        'options': ['10', '9', '11', '12'],
                        'answer': '10',
                        'hint': 'Add 2 more to 8.'
                    },
                    {
                        'text': 'Count by 5s: 5, 10, 15, 20, ___. What number comes next?',
                        'options': ['25', '22', '30', '24'],
                        'answer': '25',
                        'hint': 'The numbers alternate ending in 5 and 0.'
                    },
                    {
                        'text': 'Count backwards by 10s: 50, 40, 30, ___. What number comes next?',
                        'options': ['20', '25', '10', '35'],
                        'answer': '20',
                        'hint': 'Take away 10 from 30.'
                    }
                ]
            },
            {
                'title': 'Friendly Double Magic [Demo Data]',
                'description': 'Master the power of doubles and near-doubles to calculate like lightning!',
                'difficulty': 'Medium',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'What is the double of 6 (6 + 6)?',
                        'options': ['12', '11', '13', '14'],
                        'answer': '12',
                        'hint': 'Think of a dozen eggs in an egg carton!'
                    },
                    {
                        'text': 'If 7 + 7 = 14, what is the near-double 7 + 8?',
                        'options': ['15', '14', '16', '13'],
                        'answer': '15',
                        'hint': 'Just add 1 more to 14!'
                    },
                    {
                        'text': 'What number doubled gives 18?',
                        'options': ['9', '8', '7', '10'],
                        'answer': '9',
                        'hint': '9 + 9 = 18.'
                    }
                ]
            },
            {
                'title': 'Snack Shop Math [Demo Data]',
                'description': 'Buy apples, juice boxes, and cookies at the school fair and make correct change!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'An apple costs 3 coins and a juice box costs 4 coins. How many coins do you need for both?',
                        'options': ['7 coins', '6 coins', '8 coins', '12 coins'],
                        'answer': '7 coins',
                        'hint': 'Add 3 + 4.'
                    },
                    {
                        'text': 'You pay with a 10-coin note for a 7-coin snack. How much change do you get back?',
                        'options': ['3 coins', '2 coins', '4 coins', '1 coin'],
                        'answer': '3 coins',
                        'hint': '10 - 7 = 3.'
                    },
                    {
                        'text': 'How many 5-cent coins make up 20 cents?',
                        'options': ['4 coins', '3 coins', '5 coins', '2 coins'],
                        'answer': '4 coins',
                        'hint': 'Count: 5, 10, 15, 20... that is 4 coins!'
                    }
                ]
            },

            # --- Ages 9-12 ---
            {
                'title': 'Multi-Step Math Wizard [Demo Data]',
                'description': 'Solve multi-step story quests involving grouping, multiplication, and secret codes!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'What is 8 x 7?',
                        'options': ['56', '54', '58', '64'],
                        'answer': '56',
                        'hint': 'Remember: 5, 6, 7, 8 -> 56 = 7 x 8!'
                    },
                    {
                        'text': 'You have 24 candies shared equally among 4 friends. How many candies does each friend receive?',
                        'options': ['6', '4', '8', '7'],
                        'answer': '6',
                        'hint': 'Divide 24 by 4.'
                    },
                    {
                        'text': 'Calculate: (5 + 3) x 4.',
                        'options': ['32', '17', '28', '24'],
                        'answer': '32',
                        'hint': 'Solve inside brackets first: 5 + 3 = 8, then 8 x 4 = 32.'
                    }
                ]
            },
            {
                'title': 'KenKen Mini Puzzles [Demo Data]',
                'description': 'Use target operations (+, -, x, /) inside cage outlines on a 3x3 mathematical grid!',
                'difficulty': 'Medium',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'In a 3x3 grid using numbers 1, 2, 3: A 2-cell cage has target "6x". What two numbers fill the cage?',
                        'options': ['2 and 3', '1 and 5', '3 and 3', '1 and 6'],
                        'answer': '2 and 3',
                        'hint': '2 times 3 equals 6, and both digits are between 1 and 3.'
                    },
                    {
                        'text': 'A 2-cell cage has target "1-". If one cell is 3, what must the other cell be?',
                        'options': ['2', '1', '3', '4'],
                        'answer': '2',
                        'hint': '3 - 2 = 1.'
                    },
                    {
                        'text': 'What is the sum of all digits from 1 to 3 in any single row or column of a 3x3 grid?',
                        'options': ['6', '5', '7', '9'],
                        'answer': '6',
                        'hint': '1 + 2 + 3 = 6.'
                    }
                ]
            },
            {
                'title': 'Secret Fraction Pizza [Demo Data]',
                'description': 'Slice delicious visual pizzas into halves, quarters, eighths, and equivalent slices!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'A pizza is cut into 8 equal slices. Leo eats 4 slices. What fraction of the pizza did Leo eat?',
                        'options': ['1/2 (one half)', '1/4', '3/8', '2/3'],
                        'answer': '1/2 (one half)',
                        'hint': '4 out of 8 slices is exactly half of the pizza.'
                    },
                    {
                        'text': 'Which fraction is equivalent to 2/4?',
                        'options': ['1/2', '1/3', '3/4', '2/8'],
                        'answer': '1/2',
                        'hint': 'Divide top and bottom by 2.'
                    },
                    {
                        'text': 'What is 1/4 + 2/4?',
                        'options': ['3/4', '3/8', '2/4', '1/2'],
                        'answer': '3/4',
                        'hint': 'Keep the same denominator (4) and add the numerators: 1 + 2 = 3.'
                    }
                ]
            },
            {
                'title': 'Prime & Multiple Hunt [Demo Data]',
                'description': 'Hunt down prime numbers, build factor trees, and uncover common multiples!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Which of these numbers is a prime number (has only two factors: 1 and itself)?',
                        'options': ['13', '12', '15', '9'],
                        'answer': '13',
                        'hint': '13 cannot be divided evenly by 2, 3, 4, etc.'
                    },
                    {
                        'text': 'What is the Least Common Multiple (LCM) of 4 and 6?',
                        'options': ['12', '24', '8', '18'],
                        'answer': '12',
                        'hint': 'List multiples: 4, 8, 12... and 6, 12... 12 is the first match!'
                    },
                    {
                        'text': 'What is the Greatest Common Factor (GCF) of 18 and 24?',
                        'options': ['6', '3', '2', '12'],
                        'answer': '6',
                        'hint': '6 divides both 18 (6x3) and 24 (6x4).'
                    }
                ]
            },

            # --- Ages 12-14 ---
            {
                'title': 'Pre-Algebra Mystery X [Demo Data]',
                'description': 'Balance two-pan scales and solve linear equations to discover secret variable X!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'If 2x + 5 = 17, what is the value of x?',
                        'options': ['6', '5', '7', '8'],
                        'answer': '6',
                        'hint': 'Subtract 5 from 17 to get 12, then divide 12 by 2: x = 6.'
                    },
                    {
                        'text': 'On a balance scale, 3 mystery boxes plus 2 kg balances 14 kg. What does each box weigh?',
                        'options': ['4 kg', '3 kg', '5 kg', '6 kg'],
                        'answer': '4 kg',
                        'hint': '3b + 2 = 14 -> 3b = 12 -> b = 4.'
                    },
                    {
                        'text': 'Simplify the expression: 4(x + 3) - 2x.',
                        'options': ['2x + 12', '2x + 3', '4x + 12', '6x + 3'],
                        'answer': '2x + 12',
                        'hint': 'Distribute 4: 4x + 12, then subtract 2x to get 2x + 12.'
                    }
                ]
            },
            {
                'title': 'Probability Carnival [Demo Data]',
                'description': 'Calculate odds on dice rolls, spinners, and mystery bag selections!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'What is the probability of rolling an even number (2, 4, or 6) on a standard 6-sided die?',
                        'options': ['3/6 or 1/2 (50%)', '1/6', '2/6', '4/6'],
                        'answer': '3/6 or 1/2 (50%)',
                        'hint': 'There are 3 even numbers out of 6 possible sides.'
                    },
                    {
                        'text': 'A bag holds 3 red marbles and 7 blue marbles. What is the chance of drawing a red marble at random?',
                        'options': ['3/10 (30%)', '7/10 (70%)', '3/7', '1/3'],
                        'answer': '3/10 (30%)',
                        'hint': 'Divide the desired count (3) by total marbles (3 + 7 = 10).'
                    },
                    {
                        'text': 'If you flip a fair coin twice, what is the probability of getting Heads on BOTH flips?',
                        'options': ['1/4 (25%)', '1/2 (50%)', '1/3', '3/4'],
                        'answer': '1/4 (25%)',
                        'hint': 'Multiply the independent probabilities: 1/2 x 1/2 = 1/4.'
                    }
                ]
            },
            {
                'title': 'Ratio & Scale Master [Demo Data]',
                'description': 'Scale up secret recipe batches and compute real-world map distances using ratios!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'A cookie recipe uses 2 cups of sugar for every 3 cups of flour. If you use 6 cups of flour, how much sugar is needed?',
                        'options': ['4 cups', '3 cups', '5 cups', '6 cups'],
                        'answer': '4 cups',
                        'hint': 'Flour doubled from 3 to 6, so sugar doubles from 2 to 4.'
                    },
                    {
                        'text': 'On an adventure map, 1 cm represents 5 kilometers. If two mountain peaks are 4 cm apart on the map, what is their real distance?',
                        'options': ['20 kilometers', '15 kilometers', '25 kilometers', '9 kilometers'],
                        'answer': '20 kilometers',
                        'hint': 'Multiply 4 cm by 5 km/cm: 4 x 5 = 20 km.'
                    },
                    {
                        'text': 'A cyclist pedals at a steady speed of 15 km/h. How far does she travel in 3 hours?',
                        'options': ['45 kilometers', '30 kilometers', '50 kilometers', '18 kilometers'],
                        'answer': '45 kilometers',
                        'hint': 'Distance = Speed x Time: 15 x 3 = 45 km.'
                    }
                ]
            },
            {
                'title': 'Financial Super-Saver [Demo Data]',
                'description': 'Calculate store discounts, sales tax, unit pricing, and smart budgeting goals!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'A skateboard originally priced at $80 is on sale with a 25% discount. What is the sale price?',
                        'options': ['$60', '$65', '$70', '$55'],
                        'answer': '$60',
                        'hint': '25% of $80 is $20. Subtract $20 from $80 = $60.'
                    },
                    {
                        'text': 'Shop A sells 4 notebooks for $12. Shop B sells 5 notebooks for $10. Which shop has the cheaper price per notebook?',
                        'options': ['Shop B ($2.00 each vs Shop A $3.00 each)', 'Shop A', 'Both are equal', 'Cannot tell'],
                        'answer': 'Shop B ($2.00 each vs Shop A $3.00 each)',
                        'hint': 'Find unit price: $12/4 = $3.00 vs $10/5 = $2.00.'
                    },
                    {
                        'text': 'You deposit $100 in a savings account with 5% annual simple interest. How much total money is in the account after 1 year?',
                        'options': ['$105', '$110', '$100', '$150'],
                        'answer': '$105',
                        'hint': 'Interest earned = $100 x 0.05 = $5. Total = $100 + $5 = $105.'
                    }
                ]
            },
            {
                'title': 'Treasure Count Island [Demo Data]',
                'description': 'Count shiny pirate coins, golden keys, and parrot feathers one by one!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'You find 3 gold doubloons in a treasure chest and 2 on the sandy beach. How many doubloons in all?',
                        'options': ['5 doubloons', '4 doubloons', '6 doubloons', '3 doubloons'],
                        'answer': '5 doubloons',
                        'hint': 'Count them up: 3... then 4, 5!'
                    },
                    {
                        'text': 'Which number is the biggest: 2, 7, 4, or 1?',
                        'options': ['7', '2', '4', '1'],
                        'answer': '7',
                        'hint': '7 is more than 2, 4, or 1 on the number line!'
                    },
                    {
                        'text': 'If you have 4 pirate hats and give 1 to the captain, how many hats do you have left?',
                        'options': ['3 hats', '2 hats', '4 hats', '5 hats'],
                        'answer': '3 hats',
                        'hint': 'Take 1 away from 4: count backwards one step.'
                    },
                    {
                        'text': 'How many wheels does a bicycle have when riding along the dock?',
                        'options': ['2 wheels', '1 wheel', '4 wheels', '3 wheels'],
                        'answer': '2 wheels',
                        'hint': 'One wheel in the front, and one wheel in the back!'
                    },
                    {
                        'text': 'Count the sides of a triangle painted on the pirate flag: 1, 2, ___?',
                        'options': ['3', '4', '5', '6'],
                        'answer': '3',
                        'hint': 'Tri means three, like a tricycle!'
                    }
                ]
            },
            {
                'title': 'Fraction Feast Bakery [Demo Data]',
                'description': 'Slice cakes, balance recipes, and master fractions, decimals, and ratios!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Chef Pierre cuts a chocolate tart into 8 equal slices. If guests eat 6 slices, what fraction of the tart remains?',
                        'options': ['2/8 (or 1/4)', '6/8 (or 3/4)', '1/8', '4/8 (or 1/2)'],
                        'answer': '2/8 (or 1/4)',
                        'hint': '8 slices minus 6 slices leaves 2 slices out of 8.'
                    },
                    {
                        'text': 'Which fraction is equivalent to one half (1/2)?',
                        'options': ['4/8', '3/8', '2/6', '5/12'],
                        'answer': '4/8',
                        'hint': 'Divide both top and bottom of 4/8 by 4.'
                    },
                    {
                        'text': 'Convert the decimal 0.75 into a simple fraction in lowest terms.',
                        'options': ['3/4', '1/4', '7/5', '75/10'],
                        'answer': '3/4',
                        'hint': '75 cents is three quarters of a whole dollar.'
                    },
                    {
                        'text': 'A muffin recipe uses 2 cups of blueberries for every 3 cups of flour. What is the ratio of blueberries to flour?',
                        'options': ['2:3', '3:2', '1:2', '2:5'],
                        'answer': '2:3',
                        'hint': 'List blueberries first (2), then flour second (3).'
                    },
                    {
                        'text': 'If a pizza costs $16.00 and is on sale for 25% off, how much money do you save?',
                        'options': ['$4.00', '$2.00', '$8.00', '$5.00'],
                        'answer': '$4.00',
                        'hint': '25% is one-fourth (1/4). 16 divided by 4 is 4.'
                    }
                ]
            },
            {
                'title': 'Prime Code Breakers [Demo Data]',
                'description': 'Crack cryptographic puzzles using prime numbers, factors, exponents, and order of operations!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Which of the following numbers is a PRIME number (divisible only by 1 and itself)?',
                        'options': ['29', '21', '25', '27'],
                        'answer': '29',
                        'hint': '21 is 3x7, 25 is 5x5, 27 is 3x9. Which number has no other factors?'
                    },
                    {
                        'text': 'Evaluate using order of operations (PEMDAS): 6 + 4 x (5 - 2)^2. What is the answer?',
                        'options': ['42', '90', '30', '54'],
                        'answer': '42',
                        'hint': '(5 - 2) = 3. 3^2 = 9. 4 x 9 = 36. 6 + 36 = 42.'
                    },
                    {
                        'text': 'What is the Greatest Common Factor (GCF) of the numbers 24 and 36?',
                        'options': ['12', '6', '8', '18'],
                        'answer': '12',
                        'hint': '12 divides evenly into both 24 (x2) and 36 (x3), and is the largest such number.'
                    },
                    {
                        'text': 'Simplify this exponential expression: (2^3) x (2^4). What is the value?',
                        'options': ['2^7 (128)', '2^12 (4096)', '4^7', '2^1 (2)'],
                        'answer': '2^7 (128)',
                        'hint': 'When multiplying powers with the same base, add the exponents: 3 + 4 = 7.'
                    },
                    {
                        'text': 'If 3x - 7 = 14, what is the value of x?',
                        'options': ['7', '6', '8', '5'],
                        'answer': '7',
                        'hint': 'Add 7 to both sides: 3x = 21. Then divide by 3: 21 / 3 = 7.'
                    }
                ]
            },
            {
                'title': 'Treasure Counting Cove [Demo Data]',
                'description': 'Count sparkling gems, compare treasure chests, and share tasty tropical berries with friendly pirate parrots!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Captain Sandy opened a pouch with 4 gold coins and added 1 more shiny coin. How many coins are in the pouch now?',
                        'options': ['3 coins', '4 coins', '5 coins', '6 coins'],
                        'answer': '5 coins',
                        'hint': 'Count up by one: after 4 comes 5!'
                    },
                    {
                        'text': 'Which treasure chest holds MORE sparkling rubies: Chest A with 7 rubies, or Chest B with 3 rubies?',
                        'options': ['Chest A with 7 rubies', 'Chest B with 3 rubies', 'Both have the same amount', 'Neither has rubies'],
                        'answer': 'Chest A with 7 rubies',
                        'hint': '7 is greater than 3.'
                    },
                    {
                        'text': 'Count the friendly sea turtles swimming near the coral: 🐢 🐢 🐢. How many turtles do you count?',
                        'options': ['2 turtles', '3 turtles', '4 turtles', '5 turtles'],
                        'answer': '3 turtles',
                        'hint': 'Tap and count each one: one, two, three!'
                    },
                    {
                        'text': 'If you have 5 sweet blueberries and share 2 with your friend, how many blueberries do you have left?',
                        'options': ['1 blueberry', '2 blueberries', '3 blueberries', '4 blueberries'],
                        'answer': '3 blueberries',
                        'hint': 'Hold up 5 fingers and put 2 down.'
                    },
                    {
                        'text': 'What friendly number comes immediately before 6 when counting up from 1?',
                        'options': ['4', '5', '7', '8'],
                        'answer': '5',
                        'hint': 'Count along: 1, 2, 3, 4, 5, 6!'
                    }
                ]
            },
            {
                'title': 'Rocket Countdown Sequence [Demo Data]',
                'description': 'Blast off into space by skip-counting, finding missing pattern numbers, and solving arithmetic fact families!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Mission Control does a countdown by twos: 10, 8, 6, 4, ... What number comes next before liftoff?',
                        'options': ['3', '2', '1', '0'],
                        'answer': '2',
                        'hint': 'Subtract 2 from 4.'
                    },
                    {
                        'text': 'An astronaut gathers star gems in pouches of 5. She has 4 pouches. How many gems does she have in total?',
                        'options': ['15 gems', '20 gems', '25 gems', '30 gems'],
                        'answer': '20 gems',
                        'hint': 'Skip count by fives 4 times: 5, 10, 15, 20!'
                    },
                    {
                        'text': 'Identify the missing number in this celestial coordinates sequence: 12, 15, 18, __, 24. What number fits?',
                        'options': ['19', '20', '21', '22'],
                        'answer': '21',
                        'hint': 'Each jump adds 3 to the previous number: 18 + 3 = 21.'
                    },
                    {
                        'text': 'A lunar rover has 14 battery cells. During a crater drive, it uses 6 cells. How many cells remain fully charged?',
                        'options': ['6 cells', '7 cells', '8 cells', '9 cells'],
                        'answer': '8 cells',
                        'hint': 'Calculate 14 minus 6.'
                    },
                    {
                        'text': 'Which equation belongs to the mathematical fact family for the numbers 4, 6, and 10?',
                        'options': ['6 + 4 = 10', '10 + 4 = 14', '6 - 4 = 2', '4 + 4 = 8'],
                        'answer': '6 + 4 = 10',
                        'hint': 'Fact families connect the exact same trio of numbers using addition and subtraction.'
                    }
                ]
            },
            {
                'title': 'Mini Sudoku Matrix Quest [Demo Data]',
                'description': 'Complete 4x4 Mini Sudoku grids, balance algebraic scales, and solve multi-step treasure distribution riddles!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'In a 4x4 Mini Sudoku, every row and column must contain digits 1, 2, 3, and 4. A row has [1, 4, 2, ?]. What is the missing number?',
                        'options': ['1', '2', '3', '4'],
                        'answer': '3',
                        'hint': 'Look at which digit from 1 to 4 is missing from the list.'
                    },
                    {
                        'text': 'A 2x2 corner block in a mini sudoku puzzle contains the numbers 2, 3, and 4. What digit must go into the fourth empty cell?',
                        'options': ['1', '2', '3', '4'],
                        'answer': '1',
                        'hint': 'Each 2x2 block must contain every digit from 1 through 4 exactly once.'
                    },
                    {
                        'text': 'Solve this number riddle: I am a two-digit number. My tens digit is 3. My units digit is double my tens digit. What number am I?',
                        'options': ['33', '35', '36', '38'],
                        'answer': '36',
                        'hint': 'The tens digit is 3. Double of 3 is 6, so the units digit is 6.'
                    },
                    {
                        'text': 'A team of 4 archaeologists uncovers 48 bronze medallions. If they divide the discovery equally, how many medallions does each person get?',
                        'options': ['10 medallions', '11 medallions', '12 medallions', '14 medallions'],
                        'answer': '12 medallions',
                        'hint': 'Divide 48 by 4: 48 / 4 = 12.'
                    },
                    {
                        'text': 'If three identical energy crystals plus 5 equal 26 (3C + 5 = 26), what is the value of one energy crystal C?',
                        'options': ['6', '7', '8', '9'],
                        'answer': '7',
                        'hint': 'Subtract 5 from 26 to get 21. Then divide 21 by 3 to get 7.'
                    }
                ]
            },
            {
                'title': 'Cipher Code Arithmetic [Demo Data]',
                'description': 'Crack algebraic substitution ciphers, exponential scaling rates, and multi-variable ratios in the cryptography lab!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In an encrypted transmission, variable Z satisfies: 4Z - 7 = 25. What is the numerical value of Z?',
                        'options': ['6', '7', '8', '9'],
                        'answer': '8',
                        'hint': 'Add 7 to both sides: 4Z = 32. Divide both sides by 4 to get Z = 8.'
                    },
                    {
                        'text': 'A computer simulation doubles its processing nodes every hour. Starting with 5 nodes at 1:00 PM, how many nodes exist at 4:00 PM (after 3 hours)?',
                        'options': ['20 nodes', '30 nodes', '40 nodes', '80 nodes'],
                        'answer': '40 nodes',
                        'hint': 'Compute: 5 x 2^3 = 5 x 8 = 40 nodes.'
                    },
                    {
                        'text': 'Evaluate following order of operations (PEMDAS): 18 - 3 x (4 + 2) / 2. What is the value?',
                        'options': ['6', '9', '12', '15'],
                        'answer': '9',
                        'hint': 'Parentheses: 4+2=6. Multiply: 3x6=18. Divide: 18/2=9. Subtract: 18-9=9.'
                    },
                    {
                        'text': 'A high-speed bullet train travels 150 kilometers in 45 minutes (0.75 hours). At this constant speed, how far will it travel in 1 full hour?',
                        'options': ['180 km', '200 km', '210 km', '225 km'],
                        'answer': '200 km',
                        'hint': 'Speed = distance / time = 150 / 0.75 = 200 kilometers per hour.'
                    },
                    {
                        'text': 'Two alloy weights have a ratio of 3 to 5. If their total combined weight is 64 kilograms, what is the weight of the heavier alloy?',
                        'options': ['24 kg', '35 kg', '40 kg', '48 kg'],
                        'answer': '40 kg',
                        'hint': 'Total parts = 3 + 5 = 8 parts. 64 / 8 = 8 kg per part. Heavier weight = 5 x 8 = 40 kg.'
                    }
                ]
            }
        ]
    },

    # =========================================================================
    # 4. LANGUAGE
    # =========================================================================
    {
        'name': 'Language',
        'slug': 'language',
        'icon': '📚',
        'description': 'Enhance vocabulary, phonemic awareness, reading comprehension, and grammar.',
        'activities': [
            # --- Ages 4-6 ---
            {
                'title': 'Letter Sounds [Demo Data]',
                'description': 'Sing along with alphabet letters and discover what sounds animals and objects make!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'What letter does the word "Apple" start with?',
                        'options': ['A', 'B', 'C', 'D'],
                        'answer': 'A',
                        'hint': 'It is the very first letter in the alphabet song.'
                    },
                    {
                        'text': 'What letter makes the cheerful "sss" sound in the word "Sun"?',
                        'options': ['S', 'T', 'M', 'P'],
                        'answer': 'S',
                        'hint': 'It slithers like a friendly snake.'
                    },
                    {
                        'text': 'Which playful word rhymes with "Cat"?',
                        'options': ['Bat', 'Dog', 'Fish', 'Bird'],
                        'answer': 'Bat',
                        'hint': 'They both end with the bouncy "-at" sound.'
                    }
                ]
            },
            {
                'title': 'Alphabet Safari [Demo Data]',
                'description': 'Journey through the alphabet jungle and match capital letters to their small letter friends!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which lowercase letter matches big capital "B"?',
                        'options': ['b', 'd', 'p', 'q'],
                        'answer': 'b',
                        'hint': 'A tall bat with a round tummy on the right.'
                    },
                    {
                        'text': 'What sound does the letter "M" make in "Monkey" and "Moon"?',
                        'options': ['"Mmm"', '"Buh"', '"Tee"', '"Sss"'],
                        'answer': '"Mmm"',
                        'hint': 'Rub your tummy when you eat something yummy!'
                    },
                    {
                        'text': 'Which friendly animal starts with the letter "Z"?',
                        'options': ['Zebra', 'Lion', 'Bear', 'Monkey'],
                        'answer': 'Zebra',
                        'hint': 'It has black and white stripes from A to Z!'
                    }
                ]
            },
            {
                'title': 'Rhyme Time Magic [Demo Data]',
                'description': 'Help Mother Goose find matching rhyming word pairs for fun nursery poems!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which word rhymes with "Fox"?',
                        'options': ['Box', 'Dog', 'Cat', 'Pig'],
                        'answer': 'Box',
                        'hint': 'Both end with the bouncy "-ox" sound.'
                    },
                    {
                        'text': 'Complete the poem: "Star light, star bright, first star I see to-___."',
                        'options': ['Night', 'Morning', 'Afternoon', 'Noon'],
                        'answer': 'Night',
                        'hint': 'Bright and night rhyme together.'
                    },
                    {
                        'text': 'Which word rhymes with "Tree"?',
                        'options': ['Bee', 'Rock', 'Grass', 'Cloud'],
                        'answer': 'Bee',
                        'hint': 'Bzzzz! A buzzing little insect in the tree.'
                    }
                ]
            },
            {
                'title': 'Picture-Word Match [Demo Data]',
                'description': 'Read short 3-letter CVC words and match them to colorful picture cards!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Sound out the letters: P - E - N. What handy tool do you use to write or draw?',
                        'options': ['Pen', 'Pan', 'Pin', 'Pot'],
                        'answer': 'Pen',
                        'hint': 'It writes with blue or black ink.'
                    },
                    {
                        'text': 'Sound out: H - A - T. What do you wear on your head when playing in the sun?',
                        'options': ['Hat', 'Hot', 'Hit', 'Hut'],
                        'answer': 'Hat',
                        'hint': 'It keeps the sun out of your eyes.'
                    },
                    {
                        'text': 'Sound out: C - U - P. What do you drink warm milk or fresh water from?',
                        'options': ['Cup', 'Cap', 'Cop', 'Cub'],
                        'answer': 'Cup',
                        'hint': 'It has a small handle to hold.'
                    }
                ]
            },

            # --- Ages 6-9 ---
            {
                'title': 'Word Builder [Demo Data]',
                'description': 'Explore opposites, colorful describing words, and action verbs in stories!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'What is the opposite of the word "Hot"?',
                        'options': ['Cold', 'Warm', 'Dry', 'Wet'],
                        'answer': 'Cold',
                        'hint': 'Think of an ice cube in winter.'
                    },
                    {
                        'text': 'Which describing word (adjective) fits a gigantic roaring dinosaur?',
                        'options': ['Huge', 'Tiny', 'Quiet', 'Slim'],
                        'answer': 'Huge',
                        'hint': 'It means extraordinarily big and tall.'
                    },
                    {
                        'text': 'Complete the sentence: "On a clear afternoon, the open sky is bright ___."',
                        'options': ['Blue', 'Purple', 'Running', 'Loud'],
                        'answer': 'Blue',
                        'hint': 'The cheerful color of daytime skies.'
                    }
                ]
            },
            {
                'title': 'Sentence Explorer [Demo Data]',
                'description': 'Discover exciting punctuation marks, action verbs, and plural word forms!',
                'difficulty': 'Medium',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Which of these words is an action verb that your body can do?',
                        'options': ['Jump', 'Table', 'Yellow', 'Heavy'],
                        'answer': 'Jump',
                        'hint': 'You leap off the ground with both feet!'
                    },
                    {
                        'text': 'Which punctuation mark ends an exciting exclamation like "Hurray, we solved it!"?',
                        'options': ['Exclamation mark (!)', 'Question mark (?)', 'Period (.)', 'Comma (,)'],
                        'answer': 'Exclamation mark (!)',
                        'hint': 'It shows joy, surprise, or loud excitement.'
                    },
                    {
                        'text': 'What is the plural form when you talk about more than one child?',
                        'options': ['Children', 'Childs', 'Childrens', 'Childies'],
                        'answer': 'Children',
                        'hint': 'It changes form without just adding an "s".'
                    }
                ]
            },
            {
                'title': 'Compound Word Factory [Demo Data]',
                'description': 'Snap two smaller words together to craft wonderful new compound words!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'What word do you build when you join "Sun" + "Flower"?',
                        'options': ['Sunflower', 'Sundial', 'Flowerbed', 'Sunlight'],
                        'answer': 'Sunflower',
                        'hint': 'A tall golden flower that tracks the sun across the sky.'
                    },
                    {
                        'text': 'What compound word is made from "Rain" + "Bow"?',
                        'options': ['Rainbow', 'Raincoat', 'Raindrop', 'Bowtie'],
                        'answer': 'Rainbow',
                        'hint': 'An arch of colorful ribbons in the sky after rain.'
                    },
                    {
                        'text': 'Which of these is a compound word made of two independent words?',
                        'options': ['Pancake (Pan + Cake)', 'Elephant', 'Banana', 'Tiger'],
                        'answer': 'Pancake (Pan + Cake)',
                        'hint': 'A cake you cook in a frying pan!'
                    }
                ]
            },
            {
                'title': 'Synonyms & Antonyms Safari [Demo Data]',
                'description': 'Match word twins that share meanings and opposite pairs that dance apart!',
                'difficulty': 'Medium',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Which word is a synonym (means nearly the same) for "Joyful"?',
                        'options': ['Happy', 'Angry', 'Tired', 'Bored'],
                        'answer': 'Happy',
                        'hint': 'Full of bright smiles and good cheer.'
                    },
                    {
                        'text': 'What is an antonym (opposite meaning) of the word "Brave"?',
                        'options': ['Afraid / Timid', 'Courageous', 'Strong', 'Fast'],
                        'answer': 'Afraid / Timid',
                        'hint': 'Feeling fearful instead of bold.'
                    },
                    {
                        'text': 'Which word means the opposite of "Whisper"?',
                        'options': ['Shout', 'Mumble', 'Listen', 'Sing'],
                        'answer': 'Shout',
                        'hint': 'Speaking with a very loud, booming voice.'
                    }
                ]
            },

            # --- Ages 9-12 ---
            {
                'title': 'Story Detective [Demo Data]',
                'description': 'Read short mystery paragraphs, find clue words, and deduce character motivations!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'In the story: "The valiant knight rescued the lost golden puppy from the misty forest." Who was lost?',
                        'options': ['The puppy', 'The knight', 'The forest', 'The horse'],
                        'answer': 'The puppy',
                        'hint': 'Notice which character needed saving.'
                    },
                    {
                        'text': 'Which word means the closest to "Timid"?',
                        'options': ['Shy', 'Boastful', 'Energetic', 'Loud'],
                        'answer': 'Shy',
                        'hint': 'Hesitant and quiet around new people.'
                    },
                    {
                        'text': 'What does the idiom "A piece of cake" mean when someone describes a fun puzzle?',
                        'options': ['It was very easy to accomplish', 'It tasted like chocolate', 'It was a birthday present', 'It took 10 hours'],
                        'answer': 'It was very easy to accomplish',
                        'hint': 'A common English expression for an easy task.'
                    }
                ]
            },
            {
                'title': 'Context Clue Sleuth [Demo Data]',
                'description': 'Use surrounding sentence clues to infer the meanings of unusual and vibrant words!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': '"The cavern was pitch black, so Nina turned on her flashlight to illuminate the rocky walls." What does "illuminate" mean?',
                        'options': ['To light up and make visible', 'To destroy', 'To make freezing cold', 'To paint green'],
                        'answer': 'To light up and make visible',
                        'hint': 'The flashlight helped Nina see in the darkness.'
                    },
                    {
                        'text': '"Unlike his energetic brother who ran everywhere, Liam was lethargic and stayed napping on the sofa." What does "lethargic" mean?',
                        'options': ['Sluggish, sleepy, and lacking energy', 'Hyperactive', 'Hungry', 'Excited'],
                        'answer': 'Sluggish, sleepy, and lacking energy',
                        'hint': 'The contrast with "energetic" gives away the meaning.'
                    },
                    {
                        'text': '"The ancient map was so fragile that it crumbled at the slightest touch." What does "fragile" mean?',
                        'options': ['Easily broken or delicate', 'Indestructible and heavy', 'Waterproof', 'Shiny and clean'],
                        'answer': 'Easily broken or delicate',
                        'hint': 'Think of delicate glass or brittle dry paper.'
                    }
                ]
            },
            {
                'title': 'Metaphor & Simile Sparks [Demo Data]',
                'description': 'Spark your imagination with vivid similes and poetic metaphors in narrative writing!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Which of these lines contains a simile (a comparison using "like" or "as")?',
                        'options': ['"Her laughter was as cheerful as chiming bells."', '"The classroom was a zoo."', '"Time is a thief."', '"The moon smiled down."'],
                        'answer': '"Her laughter was as cheerful as chiming bells."',
                        'hint': 'Look for the comparison word "as... as".'
                    },
                    {
                        'text': 'In the metaphor "The calm lake was a mirror reflecting the mountains", what does it mean?',
                        'options': ['The water was smooth, still, and clear', 'The lake was made of real glass', 'The lake was dangerous', 'Fish were looking in the glass'],
                        'answer': 'The water was smooth, still, and clear',
                        'hint': 'A mirror shows a clear reflection without ripples.'
                    },
                    {
                        'text': 'What literary device is used when an author writes "The whistling wind whispered secrets through the trees"?',
                        'options': ['Personification (giving human traits to nature)', 'Hyperbole', 'Alliteration', 'Onomatopoeia'],
                        'answer': 'Personification (giving human traits to nature)',
                        'hint': 'Whispering secrets is something humans do.'
                    }
                ]
            },
            {
                'title': 'Word Roots & Prefixes [Demo Data]',
                'description': 'Unlock Greek and Latin root keys (tele-, bio-, auto-) to decode hundreds of English words!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'The Greek root "tele-" appears in telescope, telephone, and television. What does "tele-" mean?',
                        'options': ['Far away or across distance', 'Underneath', 'Very small', 'Brightly colored'],
                        'answer': 'Far away or across distance',
                        'hint': 'Telescopes view far-off stars, telephones talk over distances.'
                    },
                    {
                        'text': 'The prefix "un-" in "unhappy", "unlock", and "untie" means:',
                        'options': ['Not or the reversal of an action', 'Many times', 'Very quickly', 'Inside'],
                        'answer': 'Not or the reversal of an action',
                        'hint': 'Unhappy means not happy.'
                    },
                    {
                        'text': 'The root "bio-" in "biology", "biography", and "biosphere" comes from the Greek word for:',
                        'options': ['Life or living things', 'Rocks', 'Stars', 'Water'],
                        'answer': 'Life or living things',
                        'hint': 'Biology is the scientific study of life.'
                    }
                ]
            },

            # --- Ages 12-14 ---
            {
                'title': 'Reading Deduction Lab [Demo Data]',
                'description': 'Analyze perspective, tone, subtext, and underlying themes in rich narrative passages!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Passage: "Arthur glanced at his watch for the fifth time, tapping his foot rapidly against the floorboards as the train doors remained stubbornly sealed." What can be inferred about Arthur?',
                        'options': ['He is anxious, impatient, or in a hurry', 'He is calm and about to fall asleep', 'He loves waiting on trains', 'His watch is broken'],
                        'answer': 'He is anxious, impatient, or in a hurry',
                        'hint': 'Frequent watch-checking and foot-tapping signal impatience.'
                    },
                    {
                        'text': 'What is the narrative point of view when a story uses "I", "me", and "my" to describe personal experiences?',
                        'options': ['First-person narrator', 'Second-person narrator', 'Third-person omniscient', 'Objective reporter'],
                        'answer': 'First-person narrator',
                        'hint': 'The narrator speaks directly as a character inside the story.'
                    },
                    {
                        'text': 'An author uses words like "dreary", "somber", "shadowy", and "mournful". What tone is being established?',
                        'options': ['Melancholy, sad, or foreboding', 'Humorous and lighthearted', 'Celebratory and festive', 'Technical and scientific'],
                        'answer': 'Melancholy, sad, or foreboding',
                        'hint': 'These evocative adjectives create a gloomy emotional atmosphere.'
                    }
                ]
            },
            {
                'title': 'Cryptic Word Association [Demo Data]',
                'description': 'Solve high-level semantic analogies and discover subtle relationships between abstract concepts!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Complete the analogy: Canvas is to Painter as Manuscript is to ___?',
                        'options': ['Writer / Author', 'Musician', 'Sculptor', 'Architect'],
                        'answer': 'Writer / Author',
                        'hint': 'A painter creates artwork on canvas; an author drafts work in a manuscript.'
                    },
                    {
                        'text': 'Microscope is to Microscopic as Telescope is to ___?',
                        'options': ['Distant / Celestial', 'Invisible', 'Subatomic', 'Ancient'],
                        'answer': 'Distant / Celestial',
                        'hint': 'Telescopes observe far-away objects in space.'
                    },
                    {
                        'text': 'Which pair shows the same relationship as Spark : Wildfire?',
                        'options': ['Trickle : Flood (a tiny start leading to an overwhelming event)', 'Ice : Steam', 'Sun : Moon', 'Wheel : Car'],
                        'answer': 'Trickle : Flood (a tiny start leading to an overwhelming event)',
                        'hint': 'A spark causes a wildfire; a trickle can grow into a flood.'
                    }
                ]
            },
            {
                'title': 'Argument & Evidence Judge [Demo Data]',
                'description': 'Evaluate claims, identify bias, and distinguish verified facts from opinions!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Which of the following statements is an objective, verifiable fact rather than a subjective opinion?',
                        'options': ['Water boils at 100 degrees Celsius at sea level', 'Summer is the most enjoyable season', 'Classical music is boring', 'Dogs are better pets than cats'],
                        'answer': 'Water boils at 100 degrees Celsius at sea level',
                        'hint': 'Scientific measurements can be tested and verified by anyone.'
                    },
                    {
                        'text': 'What makes a source credible when researching scientific discoveries?',
                        'options': ['Peer-reviewed publication with citations and reproducible evidence', 'High follower count on social media', 'Anonymous forum post', 'Flashy animated website banners'],
                        'answer': 'Peer-reviewed publication with citations and reproducible evidence',
                        'hint': 'Rigorous peer review verifies methodology and data accuracy.'
                    },
                    {
                        'text': 'A news report presents quotes from only one political candidate while ignoring all opposing evidence. What is this an example of?',
                        'options': ['Media bias / Selection bias', 'Balanced journalism', 'Double-blind review', 'Empirical validation'],
                        'answer': 'Media bias / Selection bias',
                        'hint': 'Selectively choosing only one perspective skews the narrative.'
                    }
                ]
            },
            {
                'title': 'Rhetorical Devices Quest [Demo Data]',
                'description': 'Deconstruct powerful persuasive speeches and discover the magic of ethos, pathos, and logos!',
                'difficulty': 'Advanced',
                'duration': 10,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In classical rhetoric, which appeal relies on logical arguments, statistics, and concrete data?',
                        'options': ['Logos', 'Pathos', 'Ethos', 'Kairos'],
                        'answer': 'Logos',
                        'hint': 'Think of "logic" — logos appeals to the rational mind.'
                    },
                    {
                        'text': '"I have told you a million times to clean your desk!" What literary figure of speech is this?',
                        'options': ['Hyperbole (deliberate exaggeration for emphasis)', 'Understatement', 'Oxymoron', 'Euphemism'],
                        'answer': 'Hyperbole (deliberate exaggeration for emphasis)',
                        'hint': 'Nobody literally speaks one million times in a row.'
                    },
                    {
                        'text': 'What rhetorical device repeats the same word or phrase at the beginning of successive sentences (e.g. "We shall fight... We shall never surrender")?',
                        'options': ['Anaphora', 'Alliteration', 'Chiasmus', 'Paradox'],
                        'answer': 'Anaphora',
                        'hint': 'Repeating the opening phrase creates rhythmic emotional power.'
                    }
                ]
            },
            {
                'title': 'Rhyme Time Meadow [Demo Data]',
                'description': 'Sing silly rhyming songs and discover words that share cheerful ending sounds!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Which animal friend rhymes with "cat" and sleeps on a fluffy rug?',
                        'options': ['Bat', 'Dog', 'Pig', 'Duck'],
                        'answer': 'Bat',
                        'hint': 'C-at rhymes with B-at and H-at!'
                    },
                    {
                        'text': 'Listen closely: "Frog, Log, Dog, ___". Which word has the same rhyming sound?',
                        'options': ['Fog', 'Sun', 'Tree', 'Fish'],
                        'answer': 'Fog',
                        'hint': 'It ends with the sound -OG!'
                    },
                    {
                        'text': 'What letter does the word "Sun" start with?',
                        'options': ['S', 'B', 'M', 'T'],
                        'answer': 'S',
                        'hint': 'It makes a hissing sound like a smiling snake!'
                    },
                    {
                        'text': 'Which word rhymes with "Blue" and sticks paper together on an art project?',
                        'options': ['Glue', 'Tape', 'Paint', 'Scissors'],
                        'answer': 'Glue',
                        'hint': 'Bl-ue rhymes with Gl-ue!'
                    },
                    {
                        'text': 'Complete the sentence: "The happy little bird sat high up in a tall green ___."',
                        'options': ['Tree', 'Car', 'Boat', 'Shoe'],
                        'answer': 'Tree',
                        'hint': 'Birds build their nests in the branches of this leafy plant!'
                    }
                ]
            },
            {
                'title': 'Compound Word Workshop [Demo Data]',
                'description': 'Hammer two smaller words together to construct fantastic new compound words!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Combine "Sun" + "Flower". What magnificent plant grows in the garden?',
                        'options': ['Sunflower', 'Sunplant', 'Flowerpot', 'Sunlight'],
                        'answer': 'Sunflower',
                        'hint': 'It is a tall flower with bright golden petals that turns toward the sun.'
                    },
                    {
                        'text': 'Which two smaller words build the compound word "Backpack"?',
                        'options': ['Back + Pack', 'Bag + Pack', 'Back + Pocket', 'Book + Pack'],
                        'answer': 'Back + Pack',
                        'hint': 'You wear the pack on your back!'
                    },
                    {
                        'text': 'What is the compound word made by combining "Rain" + "Bow"?',
                        'options': ['Rainbow', 'Rainstorm', 'Raindrop', 'Bowtie'],
                        'answer': 'Rainbow',
                        'hint': 'An arch of magical colors across a stormy sky!'
                    },
                    {
                        'text': 'Which of these words is a compound word formed from two standalone words?',
                        'options': ['Pancake', 'Muffin', 'Cookie', 'Pretzel'],
                        'answer': 'Pancake',
                        'hint': 'A cake cooked in a pan!'
                    },
                    {
                        'text': 'If you join "Butter" and "Fly", what winged beauty flutters past your window?',
                        'options': ['Butterfly', 'Dragonfly', 'Housefly', 'Firefly'],
                        'answer': 'Butterfly',
                        'hint': 'A colorful insect that transformed from a caterpillar.'
                    }
                ]
            },
            {
                'title': 'Idiom Explorer [Demo Data]',
                'description': 'Decode colorful figurative expressions and understand what they really mean!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'When someone says "it is raining cats and dogs", what do they actually mean?',
                        'options': ['It is raining very hard', 'Pets are falling from clouds', 'The weather is warm and dry', 'It is snowing heavily'],
                        'answer': 'It is raining very hard',
                        'hint': 'It is a lively exaggeration for a tremendous downpour!'
                    },
                    {
                        'text': 'If a teacher tells the class "Hold your horses!", what are they asking students to do?',
                        'options': ['Be patient and slow down', 'Ride a real horse', 'Run as fast as possible', 'Gallop in the hallway'],
                        'answer': 'Be patient and slow down',
                        'hint': 'Think about gently pulling the reins to wait a moment.'
                    },
                    {
                        'text': 'What does the phrase "a piece of cake" mean in conversation?',
                        'options': ['Something that is very easy to do', 'A slice of birthday dessert', 'A difficult challenge', 'An expensive meal'],
                        'answer': 'Something that is very easy to do',
                        'hint': 'Doing something effortless is as enjoyable as eating a sweet treat.'
                    },
                    {
                        'text': 'If your friend says "I am all ears", what are they communicating?',
                        'options': ['I am listening very carefully', 'My ears are very large', 'I cannot hear anything', 'I need earmuffs'],
                        'answer': 'I am listening very carefully',
                        'hint': 'They are giving you their full attention to listen to your story.'
                    },
                    {
                        'text': 'What does it mean to "break the ice" in a group of new classmates?',
                        'options': ['Start a conversation to help everyone feel relaxed', 'Chop a frozen pond', 'Cool down with ice cubes', 'Leave the room silently'],
                        'answer': 'Start a conversation to help everyone feel relaxed',
                        'hint': 'It relieves initial shyness when meeting new people.'
                    }
                ]
            },
            {
                'title': 'Rhyme Time Picnic [Demo Data]',
                'description': 'Sing rhyming chants, match beginning letter sounds, and discover friendly antonyms at the alphabet picnic!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': "Which friendly animal name rhymes with the word 'HAT'?",
                        'options': ['DOG', 'CAT', 'PIG', 'DUCK'],
                        'answer': 'CAT',
                        'hint': 'Listen for the ending -AT sound: H-AT and C-AT!'
                    },
                    {
                        'text': "What beginning letter sound do you hear when you say the sunny word 'SUN'?",
                        'options': ['B', 'M', 'S', 'T'],
                        'answer': 'S',
                        'hint': 'It makes a hissing sound like a friendly snake: sssss!'
                    },
                    {
                        'text': "Which word rhymes with the glowing night word 'STAR'?",
                        'options': ['MOON', 'CAR', 'CLOUD', 'TREE'],
                        'answer': 'CAR',
                        'hint': 'Listen for the ending -AR sound: St-AR and C-AR!'
                    },
                    {
                        'text': "Look at the picnic blanket! Which word is the OPPOSITE of the word 'BIG'?",
                        'options': ['TALL', 'HEAVY', 'SMALL', 'GIANT'],
                        'answer': 'SMALL',
                        'hint': 'Think of a tiny baby ladybug or a little raisin.'
                    },
                    {
                        'text': "Which letter comes right after 'A, B, C' in the alphabet song?",
                        'options': ['E', 'F', 'D', 'G'],
                        'answer': 'D',
                        'hint': 'Sing along: A, B, C, D!'
                    }
                ]
            },
            {
                'title': 'Word Safari Explorer [Demo Data]',
                'description': 'Build compound words, spot action verbs in animal stories, and expand vocabulary on a jungle safari trek!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': "Put two words together: 'RAIN' + 'BOW'. What magical arch in the sky does it create?",
                        'options': ['Raindrop', 'Rainbow', 'Raincoat', 'Rainstorm'],
                        'answer': 'Rainbow',
                        'hint': 'Combine rain and the curved bow shape seen after a shower.'
                    },
                    {
                        'text': "Which word has almost the exact SAME meaning as the word 'JOYFUL'?",
                        'options': ['Tired', 'Angry', 'Happy', 'Quiet'],
                        'answer': 'Happy',
                        'hint': 'How you feel when you are smiling and playing your favorite game.'
                    },
                    {
                        'text': "What is the opposite (antonym) of the word 'ANCIENT'?",
                        'options': ['Old', 'Giant', 'Heavy', 'Modern'],
                        'answer': 'Modern',
                        'hint': 'Something brand new and made in current times.'
                    },
                    {
                        'text': "In the sentence 'The swift cheetah dashed across the grassy plain', which word is an ACTION verb?",
                        'options': ['cheetah', 'swift', 'dashed', 'grassy'],
                        'answer': 'dashed',
                        'hint': 'Which word tells what the cheetah is actively doing?'
                    },
                    {
                        'text': 'Choose the compound word that names a buzzing insect home in a hollow tree trunk:',
                        'options': ['Birdnest', 'Beehive', 'Antfarm', 'Beaverdam'],
                        'answer': 'Beehive',
                        'hint': "Join the words 'Bee' and 'Hive' together."
                    }
                ]
            },
            {
                'title': 'Context Clue Sleuth Quest [Demo Data]',
                'description': 'Investigate context clues, analyze figurative language similes, and break down Greek and Latin word roots!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': "Read this sentence: 'The hiker was so FAMISHED after climbing the mountain peak that she ate three hearty bowls of stew.' What does FAMISHED mean?",
                        'options': ['Very exhausted', 'Extremely hungry', 'Excited and joyful', 'Chilly and shivering'],
                        'answer': 'Extremely hungry',
                        'hint': 'Look at the clue: she ate three whole hearty bowls of food!'
                    },
                    {
                        'text': "What does the figurative idiom 'burn the midnight oil' mean when working on a science fair project?",
                        'options': ['Light a camping lamp', 'Work or study late into the night', 'Start a campfire', 'Waste cooking supplies'],
                        'answer': 'Work or study late into the night',
                        'hint': 'Before electric bulbs, people burned oil lamps to study late after sunset.'
                    },
                    {
                        'text': "Which figurative language device is used in: 'The lightning flashed across the sky like a silver sword'?",
                        'options': ['Metaphor', 'Simile', 'Hyperbole', 'Alliteration'],
                        'answer': 'Simile',
                        'hint': "Look for the comparison word 'like' connecting lightning and sword."
                    },
                    {
                        'text': "Identify the prefix in the word 'RECONSTRUCT' and what it indicates:",
                        'options': ["'Re-' meaning 'again'", "'Con-' meaning 'against'", "'-struct' meaning 'to build'", "'-ruct' meaning 'broken'"],
                        'answer': "'Re-' meaning 'again'",
                        'hint': "The prefix 'Re-' added to 'construct' means to build something again."
                    },
                    {
                        'text': 'Complete the word analogy: Ocean is to Water as Forest is to ___:',
                        'options': ['Trees', 'Desert', 'Clouds', 'Rocks'],
                        'answer': 'Trees',
                        'hint': 'Water is the primary feature of an ocean, just as trees are the primary feature of a forest.'
                    }
                ]
            },
            {
                'title': 'Archaeologist Reading Crypt [Demo Data]',
                'description': 'Analyze historical expedition journals, deduce implicit textual evidence, and evaluate rhetorical techniques!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': "Read this field note: 'Although the papyrus scroll was weathered, the script revealed that the valley settlement flourished for three centuries before tectonic shifts altered the river course.' What caused the settlement decline?",
                        'options': ['Military invasions', 'Geological shifts that redirected the river', 'Trade disputes', 'Lack of writing materials'],
                        'answer': 'Geological shifts that redirected the river',
                        'hint': "Look directly at the phrase 'tectonic shifts altered the river course'."
                    },
                    {
                        'text': "What is the author's primary tone in: 'While initial field specimens look intriguing, rigorous laboratory testing is necessary before validating the hypothesis'?",
                        'options': ['Cautious and objective', 'Reckless and impulsive', 'Hostile and sarcastic', 'Overly emotional'],
                        'answer': 'Cautious and objective',
                        'hint': 'The author emphasizes careful verification and objective testing before reaching conclusions.'
                    },
                    {
                        'text': "The Greek root 'CHRON-' is found in words like 'chronology', 'chronometer', and 'synchronize'. What does this root mean?",
                        'options': ['Earth', 'Life', 'Time', 'Sound'],
                        'answer': 'Time',
                        'hint': 'Think of arranging events in time sequence or using an accurate timepiece.'
                    },
                    {
                        'text': 'Which of the following statements represents an INFERENCE rather than an explicit factual observation?',
                        'options': ['The stone tablet measures 45 centimeters in height', 'The pottery shards contain traces of olive oil', 'The ancient artisans held astronomers in high regard because star glyphs decorated all royal seals', 'Three bronze coins were uncovered in the stratum'],
                        'answer': 'The ancient artisans held astronomers in high regard because star glyphs decorated all royal seals',
                        'hint': 'An inference interprets visible clues to draw a reasoned conclusion about values or beliefs.'
                    },
                    {
                        'text': "Identify the logical fallacy: 'No scientist has ever proven that ancient sunken cities cannot exist in this trench, so one must be down there.'",
                        'options': ['Ad Hominem', 'Appeal to Ignorance', 'Bandwagon Fallacy', 'Straw Man'],
                        'answer': 'Appeal to Ignorance',
                        'hint': 'Claiming a conclusion is true simply because it has not been proven false is an Appeal to Ignorance.'
                    }
                ]
            }
        ]
    },

    # =========================================================================
    # 5. MEMORY
    # =========================================================================
    {
        'name': 'Memory',
        'slug': 'memory',
        'icon': '🧠',
        'description': 'Exercise visual recall, short-term sequence memory, and focus.',
        'activities': [
            # --- Ages 4-6 ---
            {
                'title': 'Fruit Recall [Demo Data]',
                'description': 'Take a peek inside the fruit basket and remember which delicious fruits were there!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Remember this picnic basket: 🍎 Apple, 🍌 Banana, 🍇 Grapes. Which sunny yellow fruit was inside?',
                        'options': ['Banana', 'Orange', 'Strawberry', 'Lemon'],
                        'answer': 'Banana',
                        'hint': 'Monkeys love peeling this long yellow treat.'
                    },
                    {
                        'text': 'Take a quick 2-second glance: 🐶 Playful Puppy. What friendly animal was it?',
                        'options': ['Puppy / Dog', 'Cat', 'Rabbit', 'Duck'],
                        'answer': 'Puppy / Dog',
                        'hint': 'It barks cheerfully and wags its tail!'
                    },
                    {
                        'text': 'Remember the lucky star number: 7. What was the lucky number?',
                        'options': ['7', '3', '5', '9'],
                        'answer': '7',
                        'hint': 'Between 6 and 8.'
                    }
                ]
            },
            {
                'title': 'Object Memory [Demo Data]',
                'description': 'Take a quick look at a magic tray of toys, close your eyes, and remember what you saw!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'Imagine: A red ball, a green toy car, and a blue kite. What color was the toy car?',
                        'options': ['Green', 'Red', 'Blue', 'Yellow'],
                        'answer': 'Green',
                        'hint': 'Like fresh spring grass.'
                    },
                    {
                        'text': 'You saw 3 shiny stars: ⭐ ⭐ ⭐. Exactly how many stars were on screen?',
                        'options': ['3', '2', '4', '5'],
                        'answer': '3',
                        'hint': 'Count 1, 2, 3!'
                    },
                    {
                        'text': 'Remember: Tall Tree, Flowing River, Snowy Mountain. Which word was NOT on the list?',
                        'options': ['Ocean', 'Tall Tree', 'Flowing River', 'Snowy Mountain'],
                        'answer': 'Ocean',
                        'hint': 'It was never mentioned on the trail.'
                    }
                ]
            },
            {
                'title': 'Animal Hide & Seek [Demo Data]',
                'description': 'Watch friendly farm animals scamper behind the barn, then remember who hid where!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'The brown horse ran behind the red barn, while the sheep grazed in the meadow. Who hid behind the barn?',
                        'options': ['The Horse', 'The Sheep', 'The Pig', 'The Duck'],
                        'answer': 'The Horse',
                        'hint': 'The big galloping friend with the flowing mane.'
                    },
                    {
                        'text': 'Three birds flew by: a Bluebird first, then a Red Robin. Which bird flew by first?',
                        'options': ['The Bluebird', 'The Red Robin', 'A Yellow Canary', 'An Owl'],
                        'answer': 'The Bluebird',
                        'hint': 'The blue feathered friend was at the front.'
                    },
                    {
                        'text': 'Remember this sound sequence: "Moo" ... "Baa". What sound did the cow make first?',
                        'options': ['"Moo"', '"Baa"', '"Oink"', '"Quack"'],
                        'answer': '"Moo"',
                        'hint': 'Cows say "Moo"!'
                    }
                ]
            },
            {
                'title': 'Color Memory Train [Demo Data]',
                'description': 'Watch a colorful circus train chug past, then recall the colors of its train cars!',
                'difficulty': 'Easy',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'The toy train engine was Red, followed by a Yellow car. What color was the first engine?',
                        'options': ['Red', 'Yellow', 'Green', 'Purple'],
                        'answer': 'Red',
                        'hint': 'Bright like a shiny fire truck.'
                    },
                    {
                        'text': 'Remember this color pair: Purple and Pink. Which color was mentioned second?',
                        'options': ['Pink', 'Purple', 'Orange', 'Blue'],
                        'answer': 'Pink',
                        'hint': 'The softer rosy shade came second.'
                    },
                    {
                        'text': 'The caboose at the very end of the train was Blue. What color was the caboose?',
                        'options': ['Blue', 'Red', 'Yellow', 'Black'],
                        'answer': 'Blue',
                        'hint': 'Like the blue sky.'
                    }
                ]
            },

            # --- Ages 6-9 ---
            {
                'title': 'Sequence Recall [Demo Data]',
                'description': 'Memorize secret multi-digit codes and color sequences in the correct order!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Remember this 3-digit secret clubhouse code: 4 - 8 - 2. What was the middle number?',
                        'options': ['8', '4', '2', '6'],
                        'answer': '8',
                        'hint': 'It was right between 4 and 2.'
                    },
                    {
                        'text': 'Remember this color sequence: Blue, Green, Red. What was the second color in line?',
                        'options': ['Green', 'Blue', 'Red', 'Yellow'],
                        'answer': 'Green',
                        'hint': 'Right after Blue.'
                    },
                    {
                        'text': 'You packed a lunchbox with: 🥪 Sandwich, 🍎 Apple, 🥛 Milk. What was the first item you packed?',
                        'options': ['Sandwich', 'Apple', 'Milk', 'Cookie'],
                        'answer': 'Sandwich',
                        'hint': 'Two bread slices with yummy fillings.'
                    }
                ]
            },
            {
                'title': 'Musical Note Memory [Demo Data]',
                'description': 'Listen with your mind’s ear and repeat musical bells and rhythmic patterns!',
                'difficulty': 'Medium',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Remember this musical pattern: Ding - Dong - Chime. What sound came right after Ding?',
                        'options': ['Dong', 'Chime', 'Beep', 'Clap'],
                        'answer': 'Dong',
                        'hint': 'The low bell chime in the middle.'
                    },
                    {
                        'text': 'Listen to the drumbeat: Tap - Tap - Clap - Tap. How many times did the drum "Tap"?',
                        'options': ['3 times', '2 times', '4 times', '1 time'],
                        'answer': '3 times',
                        'hint': 'Two taps at the start and one tap at the end: 2 + 1 = 3.'
                    },
                    {
                        'text': 'Remember these notes: Do - Mi - Sol. What was the highest note at the end?',
                        'options': ['Sol', 'Do', 'Mi', 'Fa'],
                        'answer': 'Sol',
                        'hint': 'The third note in the major chord.'
                    }
                ]
            },
            {
                'title': 'Backpack Memory Challenge [Demo Data]',
                'description': 'Pack your adventure backpack for a camping expedition and remember every vital tool!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'You pack 4 camping tools: Flashlight, Compass, Canteen, Map. Which item will help you see in the dark?',
                        'options': ['Flashlight', 'Compass', 'Canteen', 'Map'],
                        'answer': 'Flashlight',
                        'hint': 'It shines a beam of electric light.'
                    },
                    {
                        'text': 'In your camping list (Flashlight, Compass, Canteen, Map), what was the third item mentioned?',
                        'options': ['Canteen', 'Flashlight', 'Compass', 'Map'],
                        'answer': 'Canteen',
                        'hint': 'It holds fresh drinking water.'
                    },
                    {
                        'text': 'Which snack did you pack for energy: trail mix, pretzels, or popcorn? (List had: Trail Mix).',
                        'options': ['Trail Mix', 'Popcorn', 'Cotton Candy', 'Lollipop'],
                        'answer': 'Trail Mix',
                        'hint': 'Nuts and raisins mixed together.'
                    }
                ]
            },
            {
                'title': 'Card Flip Pairs [Demo Data]',
                'description': 'Remember card face locations on a 2x2 grid to make perfect matching pairs!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'Card 1 is a Star. Card 2 is a Heart. Card 3 is a Star. Which two cards make a matching pair of Stars?',
                        'options': ['Card 1 and Card 3', 'Card 1 and Card 2', 'Card 2 and Card 3', 'None'],
                        'answer': 'Card 1 and Card 3',
                        'hint': 'Both show the same Star symbol.'
                    },
                    {
                        'text': 'On a 2x2 grid: Top-Left is Sun, Top-Right is Moon, Bottom-Left is Moon. Where is the matching Moon?',
                        'options': ['Top-Right and Bottom-Left', 'Top-Left and Top-Right', 'Bottom-Right only', 'No match'],
                        'answer': 'Top-Right and Bottom-Left',
                        'hint': 'Both of these positions held a glowing Moon.'
                    },
                    {
                        'text': 'If you flip 4 cards and find 2 matching pairs, how many individual cards did you match in total?',
                        'options': ['4 cards', '2 cards', '6 cards', '8 cards'],
                        'answer': '4 cards',
                        'hint': 'Two pairs means 2 x 2 = 4 cards.'
                    }
                ]
            },

            # --- Ages 9-12 ---
            {
                'title': 'Pattern Retention [Demo Data]',
                'description': 'Hold complex alphanumeric sequences and symbol passwords in your mind under time limits!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Memorize this passcode: A - 3 - B - 9. What was the last character in the code?',
                        'options': ['9', '3', '7', 'B'],
                        'answer': '9',
                        'hint': 'The final single-digit number.'
                    },
                    {
                        'text': 'Remember this coordinate path: North, North, East, South. What was the third direction?',
                        'options': ['East', 'North', 'South', 'West'],
                        'answer': 'East',
                        'hint': 'Right after the two North steps.'
                    },
                    {
                        'text': 'Which 5 categories are explored on the ChildInsight platform?',
                        'options': ['Visual Learning, Logic, Numbers, Language, Memory', 'Only Math and English', 'Physics and Art', 'Music and Dance'],
                        'answer': 'Visual Learning, Logic, Numbers, Language, Memory',
                        'hint': 'The five core cognitive learning domains.'
                    }
                ]
            },
            {
                'title': 'Story Sequence Recall [Demo Data]',
                'description': 'Read an archaeological expedition log and reconstruct the timeline of discoveries from memory!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Log: "Day 1: Discovered ancient gate. Day 2: Deciphered stone hieroglyphics. Day 3: Unlocked inner chamber." What happened on Day 2?',
                        'options': ['Deciphered stone hieroglyphics', 'Discovered ancient gate', 'Unlocked inner chamber', 'Flew home'],
                        'answer': 'Deciphered stone hieroglyphics',
                        'hint': 'The stone carvings were translated on the second day.'
                    },
                    {
                        'text': 'What was the final discovery mentioned on Day 3?',
                        'options': ['Unlocked the inner chamber', 'Found a golden chariot', 'Lost the key', 'Camp was flooded'],
                        'answer': 'Unlocked the inner chamber',
                        'hint': 'The inner room was opened at the conclusion.'
                    },
                    {
                        'text': 'How many total days of expedition entries were recorded in the log?',
                        'options': ['3 days', '5 days', '7 days', '1 day'],
                        'answer': '3 days',
                        'hint': 'Day 1, Day 2, Day 3.'
                    }
                ]
            },
            {
                'title': 'Map Waypoint Memory [Demo Data]',
                'description': 'Memorize turns and landmarks along a winding treasure trail, then recall the way back safely!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Remember the route: Start at Old Oak -> Turn Left at the Stone Bridge -> Cross the Sandy Creek. What landmark is at turn #2?',
                        'options': ['The Stone Bridge', 'The Old Oak', 'Sandy Creek', 'The Lighthouse'],
                        'answer': 'The Stone Bridge',
                        'hint': 'You turn left at this masonry bridge.'
                    },
                    {
                        'text': 'To walk backwards from the end (Sandy Creek), what is the first reverse step?',
                        'options': ['Cross Sandy Creek back to the Stone Bridge', 'Go directly to Old Oak', 'Turn right into the swamp', 'Stay still'],
                        'answer': 'Cross Sandy Creek back to the Stone Bridge',
                        'hint': 'Retrace the trail in exact reverse order.'
                    },
                    {
                        'text': 'How many total waypoints were on the route from start to finish?',
                        'options': ['3 waypoints', '2 waypoints', '5 waypoints', '4 waypoints'],
                        'answer': '3 waypoints',
                        'hint': 'Old Oak (1), Stone Bridge (2), Sandy Creek (3).'
                    }
                ]
            },
            {
                'title': 'Flash Code Breaker [Demo Data]',
                'description': 'View a flash combination lock for 5 seconds and recall numbers, letters, and color rings!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'Flash combination: RED - 4 - BLUE - 7. What color was paired with the number 4?',
                        'options': ['RED', 'BLUE', 'GREEN', 'YELLOW'],
                        'answer': 'RED',
                        'hint': 'The first color-number pair.'
                    },
                    {
                        'text': 'What was the sum of the two digits in the combination (4 + 7)?',
                        'options': ['11', '10', '12', '14'],
                        'answer': '11',
                        'hint': 'Add 4 plus 7.'
                    },
                    {
                        'text': 'What was the second color shown on the lock?',
                        'options': ['BLUE', 'RED', 'PURPLE', 'ORANGE'],
                        'answer': 'BLUE',
                        'hint': 'The cool color before the number 7.'
                    }
                ]
            },

            # --- Ages 12-14 ---
            {
                'title': 'Working Memory Dual-Task [Demo Data]',
                'description': 'Keep alphanumeric codes in working memory while simultaneously solving quick mental calculations!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Hold code "DELTA-7" in your head. Quick math: what is 9 x 8? (72). Now recall: what was the letter in your code?',
                        'options': ['DELTA', 'ALPHA', 'OMEGA', 'SIGMA'],
                        'answer': 'DELTA',
                        'hint': 'The NATO phonetic alphabet word you held in working memory.'
                    },
                    {
                        'text': 'What was the number associated with DELTA in that code?',
                        'options': ['7', '8', '9', '72'],
                        'answer': '7',
                        'hint': 'Do not confuse the code number (7) with the math answer (72)!'
                    },
                    {
                        'text': 'In 2-back memory tasks, what cognitive ability is primarily being evaluated?',
                        'options': ['Continuous working memory updating and executive control', 'Long-term biographical recall', 'Muscle memory', 'Reflex speed only'],
                        'answer': 'Continuous working memory updating and executive control',
                        'hint': 'The n-back paradigm challenges real-time memory buffer manipulation.'
                    }
                ]
            },
            {
                'title': 'Forensic Detail Recall [Demo Data]',
                'description': 'Inspect a detailed detective scene for 5 seconds and recall subtle clues, footprints, and objects!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Scene brief: A wooden desk has a brass lamp on the left, an open diary with blue ink, and a silver pocket watch stopped at 3:15. What time was on the watch?',
                        'options': ['3:15', '12:00', '6:30', '9:45'],
                        'answer': '3:15',
                        'hint': 'A quarter past three.'
                    },
                    {
                        'text': 'On which side of the desk was the brass lamp sitting?',
                        'options': ['On the left', 'On the right', 'Underneath the chair', 'In the center drawer'],
                        'answer': 'On the left',
                        'hint': 'Recall the spatial position on the left.'
                    },
                    {
                        'text': 'What color was the ink in the open diary?',
                        'options': ['Blue', 'Red', 'Black', 'Green'],
                        'answer': 'Blue',
                        'hint': 'The ink color was blue.'
                    }
                ]
            },
            {
                'title': 'Complex Path Memory [Demo Data]',
                'description': 'Memorize a 7-step labyrinth maze sequence and reconstruct the reverse escape route!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Path: Forward 2, Turn Right, Forward 3, Turn Left, Forward 1. What was the very first turn you made?',
                        'options': ['Turn Right', 'Turn Left', 'Turn Around', 'U-turn'],
                        'answer': 'Turn Right',
                        'hint': 'After stepping forward 2 paces, you turned right.'
                    },
                    {
                        'text': 'How many total forward paces were taken in that sequence (2 + 3 + 1)?',
                        'options': ['6 paces', '5 paces', '7 paces', '4 paces'],
                        'answer': '6 paces',
                        'hint': 'Add 2 + 3 + 1 = 6 paces.'
                    },
                    {
                        'text': 'To reverse the final step ("Forward 1 pace after a Left turn"), what is the immediate first action?',
                        'options': ['Step backward 1 pace (or turn 180 degrees)', 'Turn left again', 'Run forward 3 paces', 'Jump'],
                        'answer': 'Step backward 1 pace (or turn 180 degrees)',
                        'hint': 'Undo the most recent motion first.'
                    }
                ]
            },
            {
                'title': 'Auditory & Semantic Chunking [Demo Data]',
                'description': 'Learn mnemonic chunking strategies to effortlessly memorize 10-item lists and phone sequences!',
                'difficulty': 'Advanced',
                'duration': 10,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Why is remembering the 10-digit number 800-555-0199 easier than remembering 8005550199 as a single block?',
                        'options': ['Chunking divides information into 3 meaningful groups (Miller 7±2 rule)', 'Hyphens change the mathematical value', 'Numbers become shorter', 'It has fewer digits'],
                        'answer': 'Chunking divides information into 3 meaningful groups (Miller 7±2 rule)',
                        'hint': 'Cognitive chunking groups bits into manageable units within working memory capacity.'
                    },
                    {
                        'text': 'What mnemonic technique uses a familiar physical building to store imagined items in different rooms?',
                        'options': ['The Method of Loci / Memory Palace', 'Acronym chaining', 'Rote flashcards', 'Semantic conditioning'],
                        'answer': 'The Method of Loci / Memory Palace',
                        'hint': 'Loci is Latin for "places" — spatial visual memory.'
                    },
                    {
                        'text': 'In the acronym HOMES (used to recall the 5 Great Lakes: Huron, Ontario, Michigan, Erie, Superior), what lake does the letter "M" represent?',
                        'options': ['Michigan', 'Mississippi', 'Missouri', 'Minnesota'],
                        'answer': 'Michigan',
                        'hint': 'Lake Michigan.'
                    }
                ]
            },
            {
                'title': 'Toy Chest Recall [Demo Data]',
                'description': 'Look into the colorful toy chest, remember what was inside, and spot what moved!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'The toy chest holds a Blue Train, a Red Ball, and a Yellow Duck. Which toy was yellow?',
                        'options': ['Yellow Duck', 'Red Ball', 'Blue Train', 'Green Frog'],
                        'answer': 'Yellow Duck',
                        'hint': 'It goes quack quack and loves bath time!'
                    },
                    {
                        'text': 'Remember this sequence: Teddy Bear, Toy Drum, Wooden Blocks. What was the first toy named?',
                        'options': ['Teddy Bear', 'Toy Drum', 'Wooden Blocks', 'Toy Airplane'],
                        'answer': 'Teddy Bear',
                        'hint': 'The cuddly furry friend led the list!'
                    },
                    {
                        'text': 'You put 3 shiny marbles in your pocket: Red, Blue, Green. Later you find Red and Green. Which one is missing?',
                        'options': ['Blue Marble', 'Yellow Marble', 'Purple Marble', 'Orange Marble'],
                        'answer': 'Blue Marble',
                        'hint': 'Think of the color of the deep sea!'
                    },
                    {
                        'text': 'In the playroom corner, the rocking horse wore a red saddle. What color was the saddle?',
                        'options': ['Red', 'Purple', 'Brown', 'Silver'],
                        'answer': 'Red',
                        'hint': 'The color of a bright red fire truck!'
                    },
                    {
                        'text': 'Remember these three breakfast treats: Pancake, Strawberry, Orange Juice. Which fruit was mentioned?',
                        'options': ['Strawberry', 'Banana', 'Blueberry', 'Apple'],
                        'answer': 'Strawberry',
                        'hint': 'A red fruit with tiny seeds on the outside.'
                    }
                ]
            },
            {
                'title': 'Melody Sequence Echo [Demo Data]',
                'description': 'Listen to notes on a musical xylophone and repeat the melodic sequence!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'The xylophone plays 3 notes in order: Do - Re - Mi. What was the middle note?',
                        'options': ['Re', 'Do', 'Mi', 'Fa'],
                        'answer': 'Re',
                        'hint': 'It comes between Do and Mi in the musical scale!'
                    },
                    {
                        'text': 'The drummer taps a rhythm: Clack, Thump, Clack, Thump. What beat comes next?',
                        'options': ['Clack', 'Thump', 'Splash', 'Boom'],
                        'answer': 'Clack',
                        'hint': 'Follow the alternating pattern: Clack, Thump, Clack, Thump...'
                    },
                    {
                        'text': 'Remember these four instrument sounds: Bell, Whistle, Drum, Flute. Which instrument was tapped third?',
                        'options': ['Drum', 'Bell', 'Whistle', 'Flute'],
                        'answer': 'Drum',
                        'hint': '1: Bell, 2: Whistle, 3: Drum!'
                    },
                    {
                        'text': 'A piano melody repeats twice: High note, Low note, High note, Low note. How many total notes were played?',
                        'options': ['4 notes', '2 notes', '6 notes', '8 notes'],
                        'answer': '4 notes',
                        'hint': 'Count them: High (1), Low (2), High (3), Low (4).'
                    },
                    {
                        'text': 'Which brass instrument has a long sliding tube that expands and shrinks to change pitch?',
                        'options': ['Trombone', 'Flute', 'Violin', 'Triangle'],
                        'answer': 'Trombone',
                        'hint': 'Musicians slide its arm back and forth smoothly!'
                    }
                ]
            },
            {
                'title': 'Dual N-Back Spatial Recall [Demo Data]',
                'description': 'Challenge working memory by tracking multi-step position grids and audio-visual cues!',
                'difficulty': 'Advanced',
                'duration': 9,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'In a 1-back spatial memory test, you signal when the current square matches the position from how many steps ago?',
                        'options': ['1 step ago', '2 steps ago', '3 steps ago', '5 steps ago'],
                        'answer': '1 step ago',
                        'hint': 'N represents the number of prior trials to compare against (here N=1).'
                    },
                    {
                        'text': 'You observe a flashing dot in a 3x3 grid: Top-Left, Center, Top-Left. Did trial 3 match trial 1 (a 2-back match)?',
                        'options': ['Yes, both occupied the Top-Left position', 'No, they were different', 'Cannot be determined', 'Center matched'],
                        'answer': 'Yes, both occupied the Top-Left position',
                        'hint': 'Count back 2 steps from trial 3: 3 is Top-Left, 2 is Center, 1 is Top-Left.'
                    },
                    {
                        'text': 'What psychological term describes the mental workbench that temporarily holds and manipulates information?',
                        'options': ['Working Memory', 'Sensory Adaptation', 'Muscle Memory', 'Episodic Forgetting'],
                        'answer': 'Working Memory',
                        'hint': 'It combines short-term retention with active cognitive processing.'
                    },
                    {
                        'text': 'A sequence of 5 letters is shown: X - M - R - M - Q. Which letter appeared in two different positions?',
                        'options': ['M', 'X', 'R', 'Q'],
                        'answer': 'M',
                        'hint': 'Letter M was shown in position 2 and position 4.'
                    },
                    {
                        'text': 'Which cognitive technique groups individual digits (e.g. 8-1-2-5-5-5-1-2-3-4) into meaningful units to expand recall capacity?',
                        'options': ['Chunking', 'Stroop effect', 'Priming', 'Echoic decay'],
                        'answer': 'Chunking',
                        'hint': 'Pioneered by George Miller: organizing items into memorable chunks.'
                    }
                ]
            },
            {
                'title': 'Picnic Basket Recall [Demo Data]',
                'description': 'Remember colorful fruits, woodland items, and the order of cheerful animal greetings in the meadow!',
                'difficulty': 'Beginner',
                'duration': 5,
                'min_age': 4,
                'max_age': 6,
                'questions': [
                    {
                        'text': 'You place 3 items in the picnic basket: a Red Apple, a Yellow Banana, and a Blue Napkin. Which item was Yellow?',
                        'options': ['The Apple', 'The Banana', 'The Napkin', 'The Sandwich'],
                        'answer': 'The Banana',
                        'hint': 'Recall the sweet curved fruit that has a sunny yellow peel.'
                    },
                    {
                        'text': 'A playful squirrel hid 3 acorns: 1 under a leaf, 1 behind a grey rock, and 1 inside a hollow tree trunk. Where was the second acorn hidden?',
                        'options': ['Under a leaf', 'Behind a grey rock', 'Inside a hollow tree trunk', 'In the flower patch'],
                        'answer': 'Behind a grey rock',
                        'hint': 'Think of the middle hiding spot mentioned in the story.'
                    },
                    {
                        'text': 'Three animal pals waved hello in this order: Puppy first, then Kitten, then Bunny. Who waved FIRST?',
                        'options': ['Bunny', 'Kitten', 'Puppy', 'Fox'],
                        'answer': 'Puppy',
                        'hint': 'Remember the very first friendly animal at the front of the line.'
                    },
                    {
                        'text': 'Chef Bear prepares a fruit smoothie with 3 berries: Strawberry, Blueberry, and Raspberry. Which berry was named in the MIDDLE?',
                        'options': ['Strawberry', 'Blueberry', 'Raspberry', 'Blackberry'],
                        'answer': 'Blueberry',
                        'hint': 'Recall the berry between Strawberry and Raspberry.'
                    },
                    {
                        'text': 'Listen to two instrument sounds in your head: DRUM, then BELL. What was the second sound?',
                        'options': ['DRUM', 'BELL', 'FLUTE', 'CYMBAL'],
                        'answer': 'BELL',
                        'hint': 'Replay the second sound that chimed after the drum.'
                    }
                ]
            },
            {
                'title': 'Magical Sound & Path Sequence [Demo Data]',
                'description': 'Follow enchanted stepping stone paths, memorize musical chime notes, and trace landmark directions on the secret map!',
                'difficulty': 'Easy',
                'duration': 6,
                'min_age': 6,
                'max_age': 9,
                'questions': [
                    {
                        'text': 'To cross the fairy stream, step on the colored stones in order: Green Frog, Yellow Lily, Brown Turtle, Grey Pebble. Which stone is THIRD?',
                        'options': ['Green Frog', 'Yellow Lily', 'Brown Turtle', 'Grey Pebble'],
                        'answer': 'Brown Turtle',
                        'hint': 'Count the sequence: 1st is Frog, 2nd is Lily, 3rd is Turtle.'
                    },
                    {
                        'text': 'A music box plays 4 chime notes: Low, High, High, Low. Which sequence matches the melody exactly?',
                        'options': ['High, Low, Low, High', 'Low, High, High, Low', 'Low, Low, High, High', 'High, High, Low, Low'],
                        'answer': 'Low, High, High, Low',
                        'hint': 'The tune begins with a Low note, has two High notes in the middle, and ends with Low.'
                    },
                    {
                        'text': "A trail map says: 'Turn Left at the windmill, Walk Past the wooden bridge, Dig near the weeping willow.' What do you do right after the windmill?",
                        'options': ['Dig near the willow', 'Walk Past the wooden bridge', 'Turn around', 'Sit and rest'],
                        'answer': 'Walk Past the wooden bridge',
                        'hint': 'Recall the action listed immediately after the windmill.'
                    },
                    {
                        'text': 'Memorize this 4-color beacon loop: Red, Yellow, Blue, Green. When the loop repeats, what color flashes right after Green?',
                        'options': ['Yellow', 'Blue', 'Red', 'Purple'],
                        'answer': 'Red',
                        'hint': 'The pattern loops right back to the beginning color.'
                    },
                    {
                        'text': 'Four friendly mascots stood in a row: Leo, Mia, Sam, and Zoe. Mia stood between Leo and Sam. Who was at the very start on the left?',
                        'options': ['Leo', 'Mia', 'Sam', 'Zoe'],
                        'answer': 'Leo',
                        'hint': 'Leo was the first friend standing on the far left.'
                    }
                ]
            },
            {
                'title': 'Map Route Chronology [Demo Data]',
                'description': 'Track navigation coordinates, recall expedition artifacts in chronological order, and practice paired-associate memory!',
                'difficulty': 'Medium',
                'duration': 7,
                'min_age': 9,
                'max_age': 12,
                'questions': [
                    {
                        'text': 'A messenger visited four mountain outposts in order: Alpha, Delta, Gamma, Beta. In which position was outpost Gamma visited?',
                        'options': ['1st', '2nd', '3rd', '4th'],
                        'answer': '3rd',
                        'hint': 'Trace the route: Alpha (1st), Delta (2nd), Gamma (3rd), Beta (4th).'
                    },
                    {
                        'text': 'Study this 5-digit station code: 7 - 3 - 9 - 1 - 4. What was the 4th digit in the sequence?',
                        'options': ['7', '3', '9', '1'],
                        'answer': '1',
                        'hint': 'Count through the positions: 1st=7, 2nd=3, 3rd=9, 4th=1.'
                    },
                    {
                        'text': 'An expedition catalogued 4 mineral specimens: Geode, Amber, Sapphire, and Quartz. Which mineral was catalogued immediately before Sapphire?',
                        'options': ['Geode', 'Amber', 'Quartz', 'Emerald'],
                        'answer': 'Amber',
                        'hint': 'Check the mineral listed right before Sapphire in the collection list.'
                    },
                    {
                        'text': 'A research submarine submerges in stages: 50m, 120m, 200m, 350m. If it resurfaces in reverse order, which depth will it reach second on the way up?',
                        'options': ['350m', '200m', '120m', '50m'],
                        'answer': '200m',
                        'hint': 'Reverse ascent order: 350m (1st), 200m (2nd), 120m (3rd), 50m (4th).'
                    },
                    {
                        'text': 'Remember this paired symbol code: Sun = Gold, Moon = Silver, Star = Copper, Cloud = Platinum. What metal was paired with Star?',
                        'options': ['Gold', 'Silver', 'Copper', 'Platinum'],
                        'answer': 'Copper',
                        'hint': 'Connect the celestial star with its assigned metallic partner.'
                    }
                ]
            },
            {
                'title': 'Complex Working Memory Matrix [Demo Data]',
                'description': 'Master dual-task working memory, reverse alphanumeric sequencing, and interference suppression challenges!',
                'difficulty': 'Advanced',
                'duration': 8,
                'min_age': 12,
                'max_age': 14,
                'questions': [
                    {
                        'text': 'Memorize this alphanumeric sequence: K-4, M-7, P-2, R-9. When reciting only the numbers in REVERSE order, what is the result?',
                        'options': ['4, 7, 2, 9', '9, 2, 7, 4', '9, 7, 4, 2', '2, 4, 7, 9'],
                        'answer': '9, 2, 7, 4',
                        'hint': 'The numbers in forward order are 4, 7, 2, 9. Reverse them starting with 9.'
                    },
                    {
                        'text': 'Five historical milestones occurred in sequence: 1 (Charter), 2 (Treaty), 3 (Assembly), 4 (Constitution), 5 (Accord). Which event occurred 2 steps prior to Event 4?',
                        'options': ['Event 1 (Charter)', 'Event 2 (Treaty)', 'Event 3 (Assembly)', 'Event 5 (Accord)'],
                        'answer': 'Event 2 (Treaty)',
                        'hint': 'Count back two steps from Event 4: one step back is 3, two steps back is 2.'
                    },
                    {
                        'text': 'In a dual-stream memory task, you observed: Red Triangle, Blue Circle, Red Square, Green Triangle, Blue Square. Which shape appeared with the color Green?',
                        'options': ['Triangle', 'Circle', 'Square', 'Hexagon'],
                        'answer': 'Triangle',
                        'hint': "Locate 'Green' in the stream and retrieve the geometric shape paired with it."
                    },
                    {
                        'text': 'Review this sequence of 6 integers: 8, 3, 5, 2, 9, 4. What is the sum of the second number and the fifth number?',
                        'options': ['10', '11', '12', '14'],
                        'answer': '12',
                        'hint': 'The second number is 3. The fifth number is 9. 3 + 9 = 12.'
                    },
                    {
                        'text': 'A transit itinerary has 4 hub transfers: Tokyo -> Singapore -> Dubai -> London -> New York. If Dubai was rerouted to Frankfurt, what is the revised 3rd hub?',
                        'options': ['Singapore', 'Dubai', 'Frankfurt', 'London'],
                        'answer': 'Frankfurt',
                        'hint': 'The 3rd hub position originally held Dubai, which was replaced by Frankfurt.'
                    }
                ]
            }
        ]
    }
]
