// Powers the visual election builder on the home page.
// No part of the algorithm lives here - this only collects the user's input
// (budget, projects, votes) and sends it to the server as simple JSON.
(function () {
  "use strict";

  const budgetEl = document.getElementById("budget");
  const projectsEl = document.getElementById("projects");
  const votersEl = document.getElementById("voters");
  const payloadEl = document.getElementById("payload");
  const form = document.getElementById("builder");
  const errorEl = document.getElementById("form-error");
  const runButton = document.getElementById("run-button");

  let nextId = 1;
  let projects = []; // [{ id, name, cost }]
  let voters = [];   // [{ id, approvals: Set<projectId> }]

  function uid() {
    return nextId++;
  }

  // Load a data object (from the server) into the on-screen builder.
  function loadData(data) {
    data = data || {};
    const idByIndex = [];
    projects = (data.projects || []).map(function (project, index) {
      const id = uid();
      idByIndex[index] = id;
      return { id: id, name: (project && project.name) || "", cost: project && project.cost != null ? String(project.cost) : "" };
    });
    voters = (data.voters || []).map(function (approvals) {
      const set = new Set();
      (approvals || []).forEach(function (index) {
        const id = idByIndex[index];
        if (id !== undefined) {
          set.add(id);
        }
      });
      return { id: uid(), approvals: set };
    });
    budgetEl.value = data.budget != null ? String(data.budget) : "";
    render();
  }

  // Keep a typed size within sensible bounds.
  function clampInt(value, min, max, fallback) {
    const parsed = Math.floor(Number(value));
    if (Number.isNaN(parsed)) {
      return fallback;
    }
    return Math.max(min, Math.min(max, parsed));
  }

  // Build a complete, ready-to-run example with the requested number of
  // projects and voters, so the user can try the algorithm without typing
  // every value by hand.
  function generateSample(numProjects, numVoters) {
    const generatedProjects = [];
    let totalCost = 0;
    let maxCost = 0;
    for (let i = 0; i < numProjects; i++) {
      const cost = 1 + Math.floor(Math.random() * 9); // 1..9
      totalCost += cost;
      maxCost = Math.max(maxCost, cost);
      generatedProjects.push({ name: "Project " + (i + 1), cost: String(cost) });
    }
    const generatedVoters = [];
    for (let v = 0; v < numVoters; v++) {
      const approvals = [];
      for (let i = 0; i < numProjects; i++) {
        if (Math.random() < 0.5) {
          approvals.push(i);
        }
      }
      if (!approvals.length && numProjects > 0) {
        approvals.push(Math.floor(Math.random() * numProjects)); // never leave a voter empty
      }
      generatedVoters.push(approvals);
    }
    // A budget big enough to fund some, but usually not all, projects.
    const budget = Math.max(maxCost, Math.round(totalCost * 0.6));
    return { budget: String(budget), projects: generatedProjects, voters: generatedVoters };
  }

  function addProject() {
    projects.push({ id: uid(), name: "", cost: "" });
    render();
    focusLastProjectName();
  }

  function removeProject(id) {
    projects = projects.filter(function (project) {
      return project.id !== id;
    });
    voters.forEach(function (voter) {
      voter.approvals.delete(id);
    });
    render();
  }

  function addVoter() {
    voters.push({ id: uid(), approvals: new Set() });
    render();
  }

  function removeVoter(id) {
    voters = voters.filter(function (voter) {
      return voter.id !== id;
    });
    render();
  }

  function projectLabel(project, index) {
    const name = (project.name || "").trim();
    return name || "Project " + (index + 1);
  }

  function renderProjects() {
    projectsEl.innerHTML = "";
    if (!projects.length) {
      const empty = document.createElement("p");
      empty.className = "muted empty-note";
      empty.textContent = "No projects yet. Click \u201c+ Add project\u201d to begin.";
      projectsEl.appendChild(empty);
      return;
    }
    projects.forEach(function (project, index) {
      const row = document.createElement("div");
      row.className = "project-row";

      const number = document.createElement("span");
      number.className = "row-index";
      number.textContent = String(index + 1);

      const nameInput = document.createElement("input");
      nameInput.type = "text";
      nameInput.className = "p-name";
      nameInput.placeholder = "e.g. New playground";
      nameInput.value = project.name;
      nameInput.addEventListener("input", function () {
        project.name = nameInput.value;
        renderVoters();
      });

      const costInput = document.createElement("input");
      costInput.type = "number";
      costInput.className = "p-cost";
      costInput.min = "0";
      costInput.step = "any";
      costInput.inputMode = "decimal";
      costInput.placeholder = "Cost";
      costInput.value = project.cost;
      costInput.addEventListener("input", function () {
        project.cost = costInput.value;
      });

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "icon-button";
      remove.setAttribute("aria-label", "Remove this project");
      remove.textContent = "\u2715";
      remove.addEventListener("click", function () {
        removeProject(project.id);
      });

      row.appendChild(number);
      row.appendChild(nameInput);
      row.appendChild(costInput);
      row.appendChild(remove);
      projectsEl.appendChild(row);
    });
  }

  function renderVoters() {
    votersEl.innerHTML = "";
    if (!voters.length) {
      const empty = document.createElement("p");
      empty.className = "muted empty-note";
      empty.textContent = "No voters yet. Click \u201c+ Add voter\u201d to begin.";
      votersEl.appendChild(empty);
      return;
    }
    voters.forEach(function (voter, voterIndex) {
      const card = document.createElement("div");
      card.className = "voter-row";

      const head = document.createElement("div");
      head.className = "voter-head";

      const title = document.createElement("strong");
      title.textContent = "Voter " + (voterIndex + 1);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "icon-button";
      remove.setAttribute("aria-label", "Remove this voter");
      remove.textContent = "\u2715";
      remove.addEventListener("click", function () {
        removeVoter(voter.id);
      });

      head.appendChild(title);
      head.appendChild(remove);
      card.appendChild(head);

      const choices = document.createElement("div");
      choices.className = "choices";
      if (!projects.length) {
        const note = document.createElement("span");
        note.className = "muted";
        note.textContent = "Add some projects first.";
        choices.appendChild(note);
      } else {
        projects.forEach(function (project, index) {
          const label = document.createElement("label");
          label.className = "choice";

          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = voter.approvals.has(project.id);
          checkbox.addEventListener("change", function () {
            if (checkbox.checked) {
              voter.approvals.add(project.id);
            } else {
              voter.approvals.delete(project.id);
            }
            label.classList.toggle("is-on", checkbox.checked);
          });

          const text = document.createElement("span");
          text.textContent = projectLabel(project, index);

          label.classList.toggle("is-on", checkbox.checked);
          label.appendChild(checkbox);
          label.appendChild(text);
          choices.appendChild(label);
        });
      }
      card.appendChild(choices);
      votersEl.appendChild(card);
    });
  }

  function render() {
    renderProjects();
    renderVoters();
  }

  function focusLastProjectName() {
    const inputs = projectsEl.querySelectorAll(".p-name");
    if (inputs.length) {
      inputs[inputs.length - 1].focus();
    }
  }

  function buildPayload() {
    return {
      budget: budgetEl.value.trim(),
      projects: projects.map(function (project) {
        return { name: project.name.trim(), cost: project.cost.trim() };
      }),
      voters: voters.map(function (voter) {
        const indices = [];
        projects.forEach(function (project, index) {
          if (voter.approvals.has(project.id)) {
            indices.push(index);
          }
        });
        return indices;
      }),
    };
  }

  function isValidNumber(text) {
    if (text === "") {
      return false;
    }
    const value = Number(text);
    return !Number.isNaN(value) && value >= 0;
  }

  function validate(payload) {
    if (!isValidNumber(payload.budget)) {
      return "Enter a budget of 0 or more.";
    }
    if (!payload.projects.length) {
      return "Add at least one project.";
    }
    const seen = new Set();
    for (let i = 0; i < payload.projects.length; i++) {
      const project = payload.projects[i];
      if (!project.name) {
        return "Project " + (i + 1) + " needs a name.";
      }
      if (seen.has(project.name)) {
        return 'Two projects are called "' + project.name + '". Use different names.';
      }
      seen.add(project.name);
      if (!isValidNumber(project.cost)) {
        return 'Enter a valid cost for "' + project.name + '".';
      }
    }
    if (!payload.voters.length) {
      return "Add at least one voter.";
    }
    return null;
  }

  function showError(message) {
    errorEl.textContent = message;
    errorEl.hidden = false;
    errorEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function hideError() {
    errorEl.hidden = true;
    errorEl.textContent = "";
  }

  form.addEventListener("submit", function (event) {
    const payload = buildPayload();
    const message = validate(payload);
    if (message) {
      event.preventDefault();
      showError(message);
      return;
    }
    hideError();
    payloadEl.value = JSON.stringify(payload);
    runButton.disabled = true;
    runButton.textContent = "Working\u2026";
  });

  document.getElementById("generate").addEventListener("click", function () {
    hideError();
    const projectsInput = document.getElementById("gen-projects");
    const votersInput = document.getElementById("gen-voters");
    const numProjects = clampInt(projectsInput.value, 1, 20, 4);
    const numVoters = clampInt(votersInput.value, 1, 50, 6);
    projectsInput.value = String(numProjects);
    votersInput.value = String(numVoters);
    loadData(generateSample(numProjects, numVoters));
  });
  document.getElementById("add-project").addEventListener("click", addProject);
  document.getElementById("add-voter").addEventListener("click", addVoter);
  document.getElementById("load-example").addEventListener("click", function () {
    hideError();
    loadData(window.EXAMPLE_DATA);
  });
  document.getElementById("clear-all").addEventListener("click", function () {
    hideError();
    loadData({ budget: "", projects: [{ name: "", cost: "" }], voters: [[]] });
  });

  const start = window.INITIAL_DATA && window.INITIAL_DATA.projects && window.INITIAL_DATA.projects.length
    ? window.INITIAL_DATA
    : window.EXAMPLE_DATA;
  loadData(start);
})();
