-- DEVELOPMENT SEED DATA — invented sample content for local development and tests.
-- This is NOT the curated knowledge base and must not be loaded into production.
-- Apply with `make db-seed` (local database only). Safe to re-run.

insert into public.symptom_categories (id, name, description) values
    ('headache',      'Headache',                'Tension-type head pain, pressure around the forehead or temples.'),
    ('nausea',        'Nausea',                  'Queasiness, motion sickness or an upset stomach.'),
    ('stress',        'Stress and anxiety',      'Feeling tense, worried, restless or overwhelmed.'),
    ('sleep',         'Difficulty sleeping',     'Trouble falling asleep or staying asleep.'),
    ('neck-shoulder', 'Neck and shoulder tension', 'Stiffness or tightness in the neck and upper shoulders.'),
    ('fatigue',       'Fatigue',                 'Low energy and tiredness.')
on conflict (id) do update
    set name = excluded.name, description = excluded.description;

insert into public.points
    (id, name, location_text, image_path, image_attribution, image_license, instructions, duration, pressure)
values
    ('LI4', 'Hegu (Union Valley)',
     'On the back of the hand, in the fleshy area between the thumb and index finger, at the highest point of the muscle when they are pressed together.',
     'dev/LI4.svg', 'Development placeholder diagram drawn for this project', 'Project-owned, free to use',
     array['Relax your hand on a table or your lap.',
           'Place the thumb of your other hand on the point and the index finger underneath for support.',
           'Press firmly and make small circles.',
           'Release slowly, then repeat on the other hand.'],
     '1–2 minutes per hand', 'Firm, but not painful'),
    ('PC6', 'Neiguan (Inner Pass)',
     'On the inner forearm, about three finger-widths above the wrist crease, between the two central tendons.',
     'dev/PC6.svg', 'Development placeholder diagram drawn for this project', 'Project-owned, free to use',
     array['Turn your palm up and place three fingers of your other hand across the wrist, starting at the crease.',
           'Find the point just above your fingers, between the two tendons.',
           'Press steadily with your thumb.'],
     '2–3 minutes per arm', 'Moderate, steady pressure'),
    ('GB20', 'Fengchi (Wind Pool)',
     'At the back of the head, in the hollows on either side of the spine where the neck muscles meet the base of the skull.',
     null, null, null,
     array['Interlace your fingers behind your head.',
           'Place your thumbs in the hollows at the base of the skull.',
           'Press upward and inward with both thumbs while breathing slowly.'],
     '1 minute', null),
    ('HT7', 'Shenmen (Spirit Gate)',
     'On the wrist crease, on the little-finger side, in the small hollow next to the tendon.',
     null, null, null,
     array['Turn your palm up.',
           'Find the hollow on the wrist crease below the little finger.',
           'Press gently and hold while breathing slowly.'],
     null, 'Gentle'),
    ('EX-HN3', 'Yintang (Hall of Impression)',
     'Midway between the inner ends of the eyebrows.',
     null, null, null,
     array['Sit comfortably and close your eyes.',
           'Place your index or middle finger between the eyebrows.',
           'Press lightly and make slow circles.'],
     null, null),
    ('GB21', 'Jianjing (Shoulder Well)',
     'On the top of the shoulder, midway between the base of the neck and the tip of the shoulder.',
     null, null, null,
     array['Reach across your body with one hand to the opposite shoulder.',
           'Find the highest point of the muscle midway along the shoulder.',
           'Squeeze and press with your fingers, then switch sides.'],
     '1 minute per side', 'Moderate'),
    ('ST36', 'Zusanli (Leg Three Miles)',
     'On the front of the lower leg, about four finger-widths below the kneecap and one finger-width toward the outside of the shin bone.',
     null, null, null,
     array['Sit with your knee bent.',
           'Place four fingers below your kneecap; the point is just below them, beside the shin bone.',
           'Press and rub firmly.'],
     null, null)
on conflict (id) do update set
    name = excluded.name, location_text = excluded.location_text, image_path = excluded.image_path,
    image_attribution = excluded.image_attribution, image_license = excluded.image_license,
    instructions = excluded.instructions, duration = excluded.duration, pressure = excluded.pressure;

insert into public.point_categories (point_id, category_id) values
    ('LI4', 'headache'), ('GB20', 'headache'), ('EX-HN3', 'headache'),
    ('PC6', 'nausea'), ('ST36', 'nausea'),
    ('HT7', 'stress'), ('EX-HN3', 'stress'), ('PC6', 'stress'),
    ('HT7', 'sleep'), ('EX-HN3', 'sleep'), ('GB20', 'sleep'),
    ('GB21', 'neck-shoulder'), ('GB20', 'neck-shoulder'), ('LI4', 'neck-shoulder'),
    ('ST36', 'fatigue'), ('LI4', 'fatigue'), ('GB21', 'fatigue')
on conflict do nothing;
