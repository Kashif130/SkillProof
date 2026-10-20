from conftest import warp_to, NOW

SKILL = "solidity"
TITLE = "Solidity"
RUBRIC = "MY-RUBRIC-XYZ Smart contracts in Solidity with tests."
OWN = "https://github.com/dev1/dev1"
SUP1 = "https://github.com/dev1/repo-a"
SUP2 = "https://gist.github.com/dev1/abc123"
LLM_PAT = r".*strict, impartial verifier for a skill claim.*"

T_PLUS_1D = "2099-01-02T00:00:00Z"
T_APPEAL_CLOSED = "2099-01-16T00:00:00Z"   # 15 days after NOW
T_REVIEW_CLOSED = "2099-03-01T00:00:00Z"
T_EXPIRED = "2100-01-02T00:00:00Z"          # > 365 days after NOW
EXPIRES_AT = "2100-01-01T00:00:00Z"


def page(body):
    return (
        "<html><body><nav>Home</nav><main>"
        f"<h1>Profile</h1><p>{body}</p></main>"
        '<section id="comments"><p>comment area</p></section>'
        "<footer>(c)</footer></body></html>"
    )


def setup_skill(contract, direct_vm, mod, skill=SKILL, title=TITLE, rubric=RUBRIC):
    direct_vm.sender = mod
    contract.add_skill(skill, title, rubric)


def mock(direct_vm, wallet, level_json='{"level": "basic"}', own_body=None, skill=SKILL,
         sup1=True, sup2=True, llm=True):
    token = f"SKP-{str(wallet).lower()}-{skill}"
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"github\.com/dev1/dev1$", {"status": 200,
                       "body": page(own_body if own_body is not None else f"About me. Ownership: {token}")})
    if sup1:
        direct_vm.mock_web(r"repo-a$", {"status": 200, "body": page("Repo A: Solidity vault with Foundry tests.")})
    if sup2:
        direct_vm.mock_web(r"gist\.github\.com", {"status": 200, "body": page("Gist: ERC20 snippet.")})
    if llm:
        direct_vm.mock_llm(LLM_PAT, level_json)


def claim(contract, direct_vm, wallet, urls=OWN, skill=SKILL, **kw):
    mock(direct_vm, wallet, skill=skill, **kw)
    direct_vm.sender = wallet
    contract.submit_claim(skill, urls)


def reject(contract, direct_vm, wallet, skill=SKILL):
    """A genuine rejection (LLM says none)."""
    claim(contract, direct_vm, wallet, skill=skill, level_json='{"level": "none"}')
