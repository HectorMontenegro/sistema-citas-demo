/**
 * Integracion opcional con un formulario que solo recibe datos ficticios.
 * Configura DEMO_API_BASE_URL y DEMO_API_TOKEN en Script Properties.
 */
function requiredProperty(name) {
  const value = PropertiesService.getScriptProperties().getProperty(name);
  if (!value) {
    throw new Error("Falta configurar " + name + " en Script Properties.");
  }
  return value;
}

function firstValue(namedValues, fieldName) {
  const values = namedValues[fieldName];
  return values && values.length > 0 ? String(values[0]).trim() : "";
}

function onFormSubmit(e) {
  if (!e || !e.namedValues) {
    throw new Error("El trigger debe ejecutarse al enviar el formulario.");
  }

  const baseUrl = requiredProperty("DEMO_API_BASE_URL").replace(/\/$/, "");
  const apiToken = requiredProperty("DEMO_API_TOKEN");
  if (!baseUrl.startsWith("https://")) {
    throw new Error("La API remota de demostracion debe utilizar HTTPS.");
  }

  const payload = {
    contact_email: firstValue(e.namedValues, "Correo de demostracion"),
    preferred_from: firstValue(e.namedValues, "Fecha minima"),
    preferred_to: firstValue(e.namedValues, "Fecha maxima")
  };

  if (!payload.contact_email || !payload.preferred_from || !payload.preferred_to) {
    throw new Error("El formulario no contiene los tres campos requeridos.");
  }

  const response = UrlFetchApp.fetch(baseUrl + "/api/requests", {
    method: "post",
    contentType: "application/json",
    headers: {"X-Demo-Token": apiToken},
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error("La API de demostracion devolvio HTTP " + status + ".");
  }

  // No se registran el correo, el token ni el contenido completo del formulario.
  console.log("Solicitud de demostracion recibida correctamente.");
}
