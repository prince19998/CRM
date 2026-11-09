USE ai_crm;

INSERT INTO leads (name, email, company, lead_source, status, notes)
VALUES
    ('Rahul Sharma',  'rahul.sharma@gmail.com',  'ABC Technologies',    'LinkedIn', 'Interested', 'Asked for a product demo and pricing details.'),
    ('Priya Patel',   'priya.patel@gmail.com',   'Bright Retail',       'Website',  'New',        'Submitted the website contact form. Interested in learning more.'),
    ('Amit Verma',    'amit.verma@gmail.com',    'Verma Logistics',     'Referral', 'Contacted',  'Referred by an existing customer. Introductory email sent.'),
    ('Sneha Iyer',    'sneha.iyer@gmail.com',    'Nexa Health',         'Event',    'Converted',  'Completed evaluation and confirmed purchase.'),
    ('Karan Mehta',   'karan.mehta@gmail.com',   'Mehta Foods',         'LinkedIn', 'Lost',       'Chose another vendor due to budget constraints.'),
    ('Ananya Rao',    'ananya.rao@gmail.com',    'CloudNine',           'Website',  'Interested', 'Requested a proposal and implementation timeline.'),
    ('Vikram Singh',  'vikram.singh@gmail.com',  'Singh Manufacturing', 'Phone',    'New',        'Initial enquiry received by phone. Needs discovery call.'),
    ('Neha Joshi',    'neha.joshi@gmail.com',    'Urban Living',        'Referral', 'Contacted',  'Follow-up email sent; awaiting response.'),
    ('Arjun Nair',    'arjun.nair@gmail.com',    'Nair Consulting',     'Email',    'Interested', 'Asked about integrations and team onboarding.'),
    ('Meera Desai',   'meera.desai@gmail.com',   'Desai Finance',       'Event',    'Converted',  'Attended event, completed trial, and converted.'),
    ('Prince Gupta', 'prince.gupta@gmail.com', 'Gupta Enterprises', 'LinkedIn', 'New', 'Initial contact via LinkedIn. Awaiting response.')
ON DUPLICATE KEY UPDATE id = id;

