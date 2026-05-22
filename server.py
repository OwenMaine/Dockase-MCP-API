import sys
import json
import traceback
import urllib.request
import urllib.error
import os

# Write logs to stderr so they don't pollute the JSON-RPC stream on stdout
def log_info(msg):
    sys.stderr.write(f"[INFO] {msg}\n")
    sys.stderr.flush()

def log_error(msg):
    sys.stderr.write(f"[ERROR] {msg}\n")
    sys.stderr.flush()

GATEWAY_URL = os.environ.get("DOCKASE_GATEWAY_URL", "http://127.0.0.1:8005")
API_KEY = os.environ.get("DOCKASE_API_KEY", "")

log_info(f"Starting Dockase MCP Server. Gateway URL: {GATEWAY_URL}")
if not API_KEY:
    log_error("DOCKASE_API_KEY environment variable is not set. API calls will fail.")

TOOLS = [
    {
        "name": "dockase_query",
        "description": "Standard legal research on Nigerian law and general legal principles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The legal principle or question to research"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "dockase_search_judgments",
        "description": "Search the Nigerian Legal judgments database (RAG search) to retrieve matching case records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The facts, case names, or legal points to search for"},
                "limit": {"type": "integer", "description": "Optional maximum number of judgments to return (default 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "dockase_analyze_contract",
        "description": "Perform senior-counsel-level legal risk review on a contract or legal text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "contract_text": {"type": "string", "description": "The full text of the contract or clause to analyze"},
                "analysis_focus": {"type": "string", "description": "Optional specific focus area, e.g., indemnity, termination, governing law"}
            },
            "required": ["contract_text"]
        }
    },
    {
        "name": "dockase_draft",
        "description": "Draft legal documents such as agreements, contracts, letters, or pleading templates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_type": {"type": "string", "description": "Type of document, e.g., 'Contract of Sale', 'NDA', 'Motion for Extension of Time'"},
                "key_facts": {"type": "string", "description": "Facts, instructions, and context to include in the draft"},
                "template_context": {"type": "string", "description": "Optional reference template text to mimic"}
            },
            "required": ["document_type", "key_facts"]
        }
    },
    {
        "name": "dockase_deep_research",
        "description": "Run an in-depth multi-step research pipeline compiling Nigerian precedents on a complex fact pattern.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fact_pattern": {"type": "string", "description": "The complex fact pattern or multi-issue scenario to research"}
            },
            "required": ["fact_pattern"]
        }
    },
    {
        "name": "dockase_chat",
        "description": "Interactive conversation with Amicus, the Dockase legal assistant agent, using CRM, task, and billing contexts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to send to the Amicus legal assistant"},
                "conversation_history": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Optional list of past messages in the conversation (role/content dicts)"
                },
                "thread_id": {"type": "string", "description": "Optional unique thread identifier to track context"}
            },
            "required": ["message"]
        }
    },
    {
        "name": "dockase_validate_citations",
        "description": "Scan a document/text, validate legal citations against the Dockase case database, and strip unverified/hallucinated ones.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The legal draft or text containing citations to check"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "dockase_similar_judgments",
        "description": "Retrieve semantically similar case precedents to a known Legal Judgment by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "judgment_id": {"type": "integer", "description": "The database ID of the source judgment"},
                "limit": {"type": "integer", "description": "Optional maximum number of similar judgments to return (default 5)"}
            },
            "required": ["judgment_id"]
        }
    },
    {
        "name": "dockase_draft_multi",
        "description": "Draft a multi-document legal set (e.g. Motion Pack: Motion + Affidavit + Written Address). Valid set keys: 'motion_pack', 'originating_pack', 'defence_pack'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_set_key": {"type": "string", "description": "The key of the document set to draft, e.g. 'motion_pack', 'originating_pack', 'defence_pack'"},
                "key_facts": {"type": "string", "description": "Facts, instructions, and context to include in the draft"},
                "template_context": {"type": "string", "description": "Optional reference template text to mimic"},
                "page_count": {"type": "string", "description": "Optional target page count range, e.g. '5-10 pages'"}
            },
            "required": ["document_set_key", "key_facts"]
        }
    },
    {
        "name": "dockase_tag_case",
        "description": "Smart rules-based case description auto-tagger. Returns list of suggested practice areas and a primary practice area.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "The description or text pattern of the legal case"},
                "case_name": {"type": "string", "description": "Optional name of the case for additional context"}
            },
            "required": ["description"]
        }
    },
    {
        "name": "dockase_list_clients",
        "description": "List the lawyer's clients stored in the CRM database.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "dockase_create_client",
        "description": "Create a new client in the CRM database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string", "description": "Full name of the client"},
                "email": {"type": "string", "description": "Optional email address of the client"},
                "phone_number": {"type": "string", "description": "Optional phone number"},
                "address": {"type": "string", "description": "Optional address details"}
            },
            "required": ["full_name"]
        }
    },
    {
        "name": "dockase_list_cases",
        "description": "List the active cases (matters) stored in the database.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "dockase_create_case",
        "description": "Create a new legal case (matter) in the database under a specific client.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_name": {"type": "string", "description": "Name/Title of the case"},
                "description": {"type": "string", "description": "Description of the legal matter"},
                "client_id": {"type": "integer", "description": "ID of the associated Client database record"},
                "case_number": {"type": "string", "description": "Optional unique court/matter case number"},
                "status": {"type": "string", "description": "Optional status, default 'OPEN'. Choices: 'OPEN', 'PENDING', 'CLOSED'"},
                "stage": {"type": "string", "description": "Optional stage, default 'INTAKE'. Choices: 'INTAKE', 'DISCOVERY', 'PRE_TRIAL', 'TRIAL', 'POST_TRIAL', 'CLOSED'"},
                "priority": {"type": "string", "description": "Optional priority, default 'MEDIUM'. Choices: 'LOW', 'MEDIUM', 'HIGH', 'URGENT'"}
            },
            "required": ["case_name", "description", "client_id"]
        }
    },
    {
        "name": "dockase_create_document",
        "description": "Upload or save a draft document directly into a specific Case file in the database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "ID of the associated Case database record"},
                "title": {"type": "string", "description": "Title of the document"},
                "content": {"type": "string", "description": "Full text or rich text content of the document"}
            },
            "required": ["case_id", "title", "content"]
        }
    },
    {
        "name": "dockase_check_freshness",
        "description": "Check document freshness alerts (stale or expiring legal docs) for a given case ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the Case"}
            },
            "required": ["case_id"]
        }
    },
    {
        "name": "dockase_list_case_updates",
        "description": "Retrieve court proceeding updates and transcription logs for a Case by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the Case"}
            },
            "required": ["case_id"]
        }
    },
    {
        "name": "dockase_log_case_update",
        "description": "Log a new court proceeding/hearing update, next hearing date, and transcription for a Case.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the Case"},
                "date": {"type": "string", "description": "Date of the hearing (YYYY-MM-DD), default is today"},
                "transcription": {"type": "string", "description": "Details of what transpired in court"},
                "next_action_plan": {"type": "string", "description": "Optional next steps before the next date"},
                "next_hearing_date": {"type": "string", "description": "Optional date of next adjourned hearing (YYYY-MM-DD)"},
                "adjournment_reason": {"type": "string", "description": "Optional reason for adjournment"}
            },
            "required": ["case_id", "transcription"]
        }
    },
    {
        "name": "dockase_summarize_case",
        "description": "Generate an AI summary of a Case description using the judgment summarization engine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the Case"}
            },
            "required": ["case_id"]
        }
    },
    {
        "name": "dockase_draft_client_email",
        "description": "Draft a professional email update to the client about their case using AI.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the Case"},
                "key_points": {"type": "string", "description": "Key details/points to convey in the email"}
            },
            "required": ["case_id", "key_points"]
        }
    }
]

def send_response(response):
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

def make_api_call(endpoint, payload=None, method="POST"):
    if not API_KEY:
        return {"success": False, "error": "DOCKASE_API_KEY environment variable is not set."}
    
    url = f"{GATEWAY_URL.rstrip('/')}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
            detail = err_json.get("detail", err_body)
        except Exception:
            detail = str(e)
        return {"success": False, "error": f"HTTP Error {e.code}: {detail}"}
    except Exception as e:
        return {"success": False, "error": f"Connection Error: {str(e)}"}

def handle_tool_call(name, arguments):
    log_info(f"Handling tool call: {name}")
    try:
        if name == "dockase_query":
            res = make_api_call("/v1/query", {"query": arguments.get("query")})
            if "response" in res:
                return {"content": [{"type": "text", "text": res["response"]}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Unknown response format')}"}], "isError": True}
            
        elif name == "dockase_search_judgments":
            res = make_api_call("/v1/judgments/search", {
                "query": arguments.get("query"),
                "limit": arguments.get("limit", 5)
            })
            if res.get("success"):
                output = f"Search Results for '{res.get('query')}':\n\n"
                for idx, item in enumerate(res.get("results", [])):
                    output += f"{idx+1}. Case: {item.get('case_name') or item.get('title')}\n"
                    output += f"   Citation: {item.get('citation')}\n"
                    output += f"   Practice Area: {item.get('practice_area')}\n"
                    output += f"   Decision: {item.get('decision')}\n"
                    output += f"   Ratio: {item.get('ratio')}\n"
                    output += f"   Summary: {item.get('summary')}\n\n"
                if not res.get("results"):
                    output += "No results found."
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Search failed')}"}], "isError": True}
            
        elif name == "dockase_analyze_contract":
            res = make_api_call("/v1/contract/analyze", {
                "contract_text": arguments.get("contract_text"),
                "focus_area": arguments.get("analysis_focus")
            })
            if res.get("success"):
                return {"content": [{"type": "text", "text": res.get("analysis", "")}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Analysis failed')}"}], "isError": True}
            
        elif name == "dockase_draft":
            res = make_api_call("/v1/draft", {
                "document_type": arguments.get("document_type"),
                "key_facts": arguments.get("key_facts"),
                "template_context": arguments.get("template_context")
            })
            if res.get("success"):
                return {"content": [{"type": "text", "text": res.get("drafted_content", "")}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Drafting failed')}"}], "isError": True}
            
        elif name == "dockase_deep_research":
            res = make_api_call("/v1/deep_research", {
                "fact_pattern": arguments.get("fact_pattern")
            })
            if res.get("success"):
                output = f"Status: {res.get('status')}\n"
                output += f"Confidence Score: {res.get('confidence_score')}\n\n"
                output += f"--- FINAL REPORT ---\n{res.get('final_report')}\n\n"
                output += "--- CITATIONS ---\n"
                for idx, c in enumerate(res.get("citations", [])):
                    output += f"- [{c.get('type')}] {c.get('title')}\n"
                output += "\n--- RESEARCH LOGS ---\n"
                for log in res.get("research_log", []):
                    output += f"- {log}\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Deep research failed')}"}], "isError": True}
            
        elif name == "dockase_chat":
            res = make_api_call("/v1/chat", {
                "message": arguments.get("message"),
                "conversation_history": arguments.get("conversation_history"),
                "thread_id": arguments.get("thread_id")
            })
            if res.get("success"):
                chat_res = res.get("response", {})
                return {"content": [{"type": "text", "text": chat_res.get("content", "")}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Chat failed')}"}], "isError": True}
            
        elif name == "dockase_validate_citations":
            res = make_api_call("/v1/citations/validate", {
                "text": arguments.get("text")
            })
            if res.get("success"):
                return {"content": [{"type": "text", "text": res.get("validated_text", "")}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Validation failed')}"}], "isError": True}
            
        elif name == "dockase_similar_judgments":
            res = make_api_call("/v1/judgments/similar", {
                "judgment_id": arguments.get("judgment_id"),
                "limit": arguments.get("limit", 5)
            })
            if res.get("success"):
                output = f"Similar Judgments for ID {res.get('judgment_id')}:\n\n"
                for idx, j in enumerate(res.get("results", [])):
                    output += f"{idx+1}. Case: {j.get('title')}\n"
                    output += f"   Citation: {j.get('citation')}\n"
                    output += f"   Practice Area: {j.get('practice_area')}\n"
                    output += f"   Similarity: {j.get('similarity')}%\n\n"
                if not res.get("results"):
                    output += "No similar judgments found."
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Failed to retrieve similar judgments')}"}], "isError": True}
            
        elif name == "dockase_draft_multi":
            res = make_api_call("/v1/draft/multi", {
                "document_set_key": arguments.get("document_set_key"),
                "key_facts": arguments.get("key_facts"),
                "template_context": arguments.get("template_context"),
                "page_count": arguments.get("page_count")
            })
            if res.get("success"):
                output = f"Successfully drafted {res.get('total_documents')} documents:\n\n"
                for doc in res.get("documents", []):
                    output += f"=== {doc.get('doc_type')} ({doc.get('title')}) ===\n"
                    output += f"{doc.get('content')}\n\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Drafting failed')}"}], "isError": True}

        elif name == "dockase_tag_case":
            res = make_api_call("/v1/cases/tag", {
                "description": arguments.get("description"),
                "case_name": arguments.get("case_name", "")
            })
            if res.get("success"):
                output = f"Auto-Tagging Results:\n"
                output += f"Primary Practice Area: {res.get('primary_practice_area')}\n"
                output += f"Suggested Tags: {', '.join(res.get('tags', []))}\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Tagging failed')}"}], "isError": True}

        elif name == "dockase_list_clients":
            res = make_api_call("/v1/clients", method="GET")
            if res.get("success"):
                output = "Clients List:\n\n"
                for c in res.get("results", []):
                    output += f"ID: {c.get('id')} - {c.get('full_name')}\n"
                    output += f"   Email: {c.get('email') or 'N/A'}\n"
                    output += f"   Phone: {c.get('phone_number') or 'N/A'}\n"
                    output += f"   Address: {c.get('address') or 'N/A'}\n\n"
                if not res.get("results"):
                    output += "No clients found."
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Listing clients failed')}"}], "isError": True}

        elif name == "dockase_create_client":
            res = make_api_call("/v1/clients", {
                "full_name": arguments.get("full_name"),
                "email": arguments.get("email"),
                "phone_number": arguments.get("phone_number"),
                "address": arguments.get("address")
            })
            if res.get("success"):
                c = res.get("client", {})
                output = f"Successfully created Client:\n"
                output += f"ID: {c.get('id')}\nName: {c.get('full_name')}\nEmail: {c.get('email') or 'N/A'}\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Creating client failed')}"}], "isError": True}

        elif name == "dockase_list_cases":
            res = make_api_call("/v1/cases", method="GET")
            if res.get("success"):
                output = "Cases (Matters) List:\n\n"
                for c in res.get("results", []):
                    output += f"ID: {c.get('id')} - {c.get('case_name')}\n"
                    output += f"   Number: {c.get('case_number') or 'N/A'}\n"
                    output += f"   Client: {c.get('client_name')} (ID: {c.get('client_id')})\n"
                    output += f"   Status: {c.get('status')} | Stage: {c.get('stage')} | Priority: {c.get('priority')}\n"
                    output += f"   Description: {c.get('description')[:100]}...\n\n"
                if not res.get("results"):
                    output += "No cases found."
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Listing cases failed')}"}], "isError": True}

        elif name == "dockase_create_case":
            res = make_api_call("/v1/cases", {
                "case_name": arguments.get("case_name"),
                "description": arguments.get("description"),
                "client_id": arguments.get("client_id"),
                "case_number": arguments.get("case_number"),
                "status": arguments.get("status", "OPEN"),
                "stage": arguments.get("stage", "INTAKE"),
                "priority": arguments.get("priority", "MEDIUM")
            })
            if res.get("success"):
                c = res.get("case", {})
                output = f"Successfully created Case:\n"
                output += f"ID: {c.get('id')}\nName: {c.get('case_name')}\nNumber: {c.get('case_number') or 'N/A'}\n"
                output += f"Client: {c.get('client_name')} (ID: {c.get('client_id')})\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Creating case failed')}"}], "isError": True}

        elif name == "dockase_create_document":
            res = make_api_call("/v1/documents", {
                "case_id": arguments.get("case_id"),
                "title": arguments.get("title"),
                "content": arguments.get("content")
            })
            if res.get("success"):
                d = res.get("document", {})
                output = f"Successfully created/uploaded document:\n"
                output += f"ID: {d.get('id')}\nTitle: {d.get('title')}\nCase ID: {d.get('case_id')}\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Creating document failed')}"}], "isError": True}

        elif name == "dockase_check_freshness":
            case_id = arguments.get("case_id")
            res = make_api_call(f"/v1/cases/{case_id}/freshness", method="GET")
            if res.get("success"):
                output = f"Document Freshness Alerts for Case ID {case_id}:\n\n"
                for a in res.get("alerts", []):
                    output += f"- Document: {a.get('document')}\n"
                    output += f"  Status: {a.get('status').upper()} ({a.get('severity').upper()} severity)\n"
                    output += f"  Alert: {a.get('message')}\n"
                    output += f"  Expiry Date: {a.get('expiry_date')}\n\n"
                if not res.get("alerts"):
                    output += "No freshness alerts. All documents are up to date."
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Failed to check freshness')}"}], "isError": True}

        elif name == "dockase_list_case_updates":
            case_id = arguments.get("case_id")
            res = make_api_call(f"/v1/cases/{case_id}/updates", method="GET")
            if res.get("success"):
                output = f"Court Updates/Proceeding Logs for Case ID {case_id}:\n\n"
                for u in res.get("results", []):
                    output += f"Date: {u.get('date')} | Logged by: {u.get('author_name')}\n"
                    output += f"Transcription: {u.get('transcription')}\n"
                    if u.get("next_action_plan"):
                        output += f"Next Action Plan: {u.get('next_action_plan')}\n"
                    output += "\n"
                if not res.get("results"):
                    output += "No court updates logged for this case."
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Failed to retrieve updates')}"}], "isError": True}

        elif name == "dockase_log_case_update":
            case_id = arguments.get("case_id")
            res = make_api_call(f"/v1/cases/{case_id}/updates", {
                "date": arguments.get("date"),
                "transcription": arguments.get("transcription"),
                "next_action_plan": arguments.get("next_action_plan"),
                "next_hearing_date": arguments.get("next_hearing_date"),
                "adjournment_reason": arguments.get("adjournment_reason")
            })
            if res.get("success"):
                u = res.get("update", {})
                output = f"Successfully logged court update (ID: {u.get('id')}) on {u.get('date')}.\n"
                if res.get("case_next_hearing_date"):
                    output += f"Next Hearing Date set to: {res.get('case_next_hearing_date')}\n"
                if res.get("case_adjournment_reason"):
                    output += f"Adjournment Reason: {res.get('case_adjournment_reason')}\n"
                return {"content": [{"type": "text", "text": output}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Failed to log update')}"}], "isError": True}

        elif name == "dockase_summarize_case":
            case_id = arguments.get("case_id")
            res = make_api_call(f"/v1/cases/{case_id}/summarize", method="POST")
            if res.get("success"):
                return {"content": [{"type": "text", "text": res.get("summary", "")}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Failed to summarize case')}"}], "isError": True}

        elif name == "dockase_draft_client_email":
            case_id = arguments.get("case_id")
            res = make_api_call(f"/v1/cases/{case_id}/draft-email", {
                "key_points": arguments.get("key_points")
            })
            if res.get("success"):
                return {"content": [{"type": "text", "text": res.get("email_draft", "")}]}
            return {"content": [{"type": "text", "text": f"Error: {res.get('error', 'Failed to draft email')}"}], "isError": True}

        else:
            return {"content": [{"type": "text", "text": f"Error: Tool '{name}' not found."}], "isError": True}
            
    except Exception as e:
        log_error(f"Error executing tool {name}: {str(e)}\n{traceback.format_exc()}")
        return {"content": [{"type": "text", "text": f"Internal Server Error: {str(e)}"}], "isError": True}

def main():
    log_info("MCP stdio loop started.")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            req = json.loads(line)
        except Exception as e:
            log_error(f"Failed to parse input line as JSON: {line}. Error: {str(e)}")
            continue
        
        req_id = req.get("id")
        method = req.get("method")
        
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "dockase-mcp",
                        "version": "1.0.0"
                    }
                }
            })
            
        elif method == "notifications/initialized":
            # No response needed for notification
            log_info("Received initialized notification.")
            
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            })
            
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = handle_tool_call(name, arguments)
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            })
            
        else:
            if req_id is not None:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    }
                })

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_info("Exiting on KeyboardInterrupt.")
    except Exception as e:
        log_error(f"Fatal error in main: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)
