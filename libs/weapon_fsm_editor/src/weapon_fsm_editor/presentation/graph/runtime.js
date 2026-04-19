(function () {
  function defaultNodeColor() {
    return {
      background: "#243447",
      border: "#6e7681",
      highlight: { background: "#243447", border: "#6e7681" },
      hover: { background: "#2d4158", border: "#8b949e" }
    };
  }

  function activeNodeColor() {
    return {
      background: "#2f81f7",
      border: "#79c0ff",
      highlight: { background: "#2f81f7", border: "#79c0ff" },
      hover: { background: "#2f81f7", border: "#79c0ff" }
    };
  }

  function defaultEdgeStyle() {
    return {
      color: { color: "#8b949e", highlight: "#8b949e", hover: "#8b949e" },
      width: 2
    };
  }

  function validEdgeStyle() {
    return {
      color: { color: "#e3b341", highlight: "#e3b341", hover: "#e3b341" },
      width: 3
    };
  }

  function lastEdgeStyle() {
    return {
      color: { color: "#4ea1ff", highlight: "#4ea1ff", hover: "#4ea1ff" },
      width: 4
    };
  }

  window.updateMachineHighlighting = function (activeStateId, validTransitionIds, lastTransitionId) {
    if (typeof nodes === "undefined" || typeof edges === "undefined") {
      return;
    }

    const validSet = new Set(validTransitionIds || []);

    nodes.update(nodes.get().map(function (node) {
      return {
        id: node.id,
        color: node.id === activeStateId ? activeNodeColor() : defaultNodeColor()
      };
    }));

    edges.update(edges.get().map(function (edge) {
      let style = defaultEdgeStyle();
      if (edge.id === lastTransitionId) {
        style = lastEdgeStyle();
      } else if (validSet.has(edge.id)) {
        style = validEdgeStyle();
      }
      return { id: edge.id, color: style.color, width: style.width };
    }));
  };

  window.fitMachineGraph = function () {
    if (typeof network === "undefined") {
      return;
    }
    network.fit({
      animation: { duration: 200, easingFunction: "easeInOutQuad" }
    });
  };

  window.zoomMachineGraph = function (scaleFactor) {
    if (typeof network === "undefined") {
      return;
    }
    const currentScale = network.getScale();
    const position = network.getViewPosition();
    network.moveTo({
      position: position,
      scale: currentScale * scaleFactor,
      animation: { duration: 100, easingFunction: "easeInOutQuad" }
    });
  };
})();
