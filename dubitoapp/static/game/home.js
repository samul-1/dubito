axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFTOKEN'
axios.defaults.headers.post['Content-Type'] = 'application/json'

function createSubmit(e) {
    e.preventDefault()
    clearFormErrors()
    const radios = document.getElementsByName('number_of_players'); 
    let number
    for(i = 0; i < radios.length; i++) { 
        if(radios[i].checked) {
            number = i + 2
        }
    }
    name_ = document.getElementById("id_creator_name").value

    let err = 0
    if(!name_.length) {
      err = 1
      appendFormError(JSON.stringify({
          "creator_name": [{"message": gettext("Campo richiesto."), "creator_name": "required"}]
      }))
    }
  
    if(err) return

    axios.post('/game/create', {
      number_of_players: number,
      creator_name: name_,
    })
    .then(function (response) {
      showGameCreated(response.data.code, response.data.number_of_players)
      ajaxPingNumberOfPlayers(response.data.game_id,response.data.number_of_players)
      console.log(response)
    })
    .catch(function (error) {
      if(error.response.status == 400)
        console.log(error.response.data)
        appendFormError(error.response.data)
    })
}

function joinSubmit(e) {
  e.preventDefault()
  clearFormErrors()
  code = document.getElementById("id_code").value
  name_ = document.getElementById("id_name").value
  let err = 0

  if(code.length != 5) {
      err = 1
      appendFormError(JSON.stringify({
          "code": [{"message": gettext("Il codice partita dev'essere esattamente di 5 cifre."), "code": ""}]
      }))
  }
  if(!name_.length) {
    err = 1
    appendFormError(JSON.stringify({
        "name": [{"message": gettext("Campo richiesto."), "name": "required"}]
    }))
  }

  if(err) return

  axios.post('/game/join_game', {
    code: code,
    name: name_,
  })
  .then(function (response) {
    window.location.replace(gameurl + response.data);
    console.log(response);
  })
  .catch(function (error) {
    if(error.response.status == 400)
      console.log(error.response.data)
      appendFormError(error.response.data)
  })
}

function feedbackSubmit(e) {
  e.preventDefault()
  clearFormErrors()
  email = document.getElementById("id_email").value
  name_ = document.getElementById("id_sender_name").value
  message = document.getElementById("id_message").value

  let err = 0

  if(!name_.length) {
    err = 1
    appendFormError(JSON.stringify({
        "sender_name": [{"message": gettext("Campo richiesto."), "name": "required"}]
    }))
  }

  if(!message.length) {
    err = 1
    appendFormError(JSON.stringify({
        "message": [{"message": gettext("Campo richiesto."), "name": "required"}]
    }))
  }

  if(err) return

  axios.post('/game/feedback', {
    email: email,
    sender_name: name_,
    message: message,
  })
  .then(function (response) {
    feedbackSuccess()
  })
  .catch(function (error) {
    if(error.response.status == 400)
      console.log(error.response.data)
      appendFormError(error.response.data)
  })
}

function feedbackSuccess() {
  document.getElementById("id_email").value = ''
  document.getElementById("id_sender_name").value = ''
  document.getElementById("id_message").value = ''

  document.getElementById("sendFeedback").style="display: none"
  document.getElementById("feedbackReceived").style="display: block"
}

function appendFormError(errData) {
  errData = JSON.parse(errData)
  fields = Object.keys(errData)
  
  for(field of fields) {
    fieldElem = document.getElementById("id_" + field)

    errorList = document.createElement("ul")
    errorList.classList.add("form_error_list")
    fieldElem.parentNode.insertBefore(errorList, fieldElem.nextSibling)

    for(let i = 0; i < errData[field].length; i++) {
      errorNode = document.createElement("li")
      errorNode.classList.add("form_error")
      errorNode.appendChild(document.createTextNode(errData[field][i]["message"]))
      errorList.appendChild(errorNode)
    }
  }
}

function clearFormErrors() {
  errorLists = document.getElementsByClassName("form_error_list")
  for(list of errorLists) {
    list.remove()
  }
  // for some reason this needs to be ran twice or it won't work properly... ugly fix but for now it'll do
  errorLists = document.getElementsByClassName("form_error_list")
  for(list of errorLists) {
    list.remove()
  }
}

function showGameCreated(code, number_of_players) {
    document.getElementById("phase1").style="display: none"
    document.getElementById("phase2").style="display: block"
    document.getElementById("gamecode").innerHTML = code
    document.getElementById("total_users").innerHTML = number_of_players
}

function ajaxPingNumberOfPlayers(game_id, number_of_players) {
    const xhttp = new XMLHttpRequest()
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            if(parseInt(this.responseText) == number_of_players) {
                location.replace(gameurl + game_id)
            } else {
                document.getElementById("user_count").innerHTML = this.responseText
            }
        }
    }
    get_joined_users = function() {
        xhttp.open("GET", "get_joined_players/" + game_id  + "/", true)
        xhttp.send()
    }
    setInterval(get_joined_users, 1000)
    animateEllipsis()
}

function stringTimes(str, times, max) {
    let res = ''
    for(let i = 0; i < times; i++) {
        res += str
    }
    for(let i = times; i < max; i++) {
        res += '&nbsp;'
    }
    return res
}

function animateEllipsis() {
    const el = document.getElementById("animatedEllipsis")
    let i = 0

    setInterval(() => {
        el.innerHTML = stringTimes('.', (i++)%4, 3)
    }, 400)
}
