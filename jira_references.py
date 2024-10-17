# REFERENCE VALUES - common mappings / bucketings for use in other processes.

# Status Categories
DONE_STATUSES = ['Done', "Won't Do"]
IN_VALIDATION_STATUSES = ['QA Ready', 'Code Review', 'In QA','Merged','Product Acceptance','Passed Integration', 'GTM']

IN_DEV_STATUSES = ['In Progress', 'Development', 'In Development']
ENG_BACKLOG_STATUSES = ['Selected for Development', 'Ready for Dev', 'Ready for Development', 'Ready', 'Ready for Planning']
PM_BACKLOG_STATUSES = ['Backlog', 'Ready for Refinement']

# Issue Type Categories
PLANNING_ISSUE_TYPES = ['Theme','Initiative']
EPIC_ISSUE_TYPES = ['Epic']
STANDARD_ISSUE_TYPES = ['Bug','DevOps Task','Release','Story','Support','Task','Test']
SUB_TASK_ISSUE_TYPES = ['Defect','DevOps Sub-task','Integration Tests','Product Acceptance Change','Sub-task']
TESTING_ISSUE_TYPES = ['Test Execution','Xray Test','Test Set','Test Plan']
                       
# Defect Category
DEFECT_ISSUE_TYPES_TO_CATEGORY = {
    "Bug": "Escaped Defect",
    "Defect": "Internal Identified Defect",
    "Product Acceptance Change": "Product Identified Defect",
    "Story": "Feature Work",
    "Task": "Feature Work",
    "Support": "Support Work"
}