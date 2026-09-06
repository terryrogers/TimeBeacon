from test_access import system, login, change


def test_defaults_validation_conflicts_and_profile_isolation(system):
    m,c=system
    assert c.get('/administration/defaults').status_code==401
    login(c)
    before=c.get('/dashboard/settings').json()['settings']['clocks']
    defaults=c.get('/administration/defaults').json()
    zones=[clock['zone'] for clock in defaults['clocks']]
    assert len(zones)==len(set(zones))==6
    body={'version':defaults['version'],'clocks':zones[::-1]}
    assert c.put('/administration/defaults',json=body).status_code==403
    for invalid in [zones[:5],zones+[zones[0]],zones[:5]+[zones[0]],zones[:5]+['Invalid/City']]:
        assert change(c,'/administration/defaults',{**body,'clocks':invalid}).status_code==422
    assert change(c,'/administration/defaults',body).status_code==200
    assert change(c,'/administration/defaults',body).status_code==409
    saved=c.get('/dashboard/settings').json()
    assert saved['settings']['clocks']==before
    assert [clock['zone'] for clock in saved['default_clocks']]==zones[::-1]
    change(c,'/administration/roles',{'name':'Clock Editor','permissions':['dashboard.view','clocks.view','clocks.amend']})
    change(c,'/administration/users',dict(username='clockeditor',password='test-password',roles=['Clock Editor']))
    login(c,'clockeditor','test-password')
    assert c.get('/admin/defaults').status_code==403
    assert c.get('/administration/defaults').status_code==403
    assert change(c,'/administration/defaults',body).status_code==403
    state=c.get('/dashboard/settings').json()
    reset=c.patch('/dashboard/settings',headers={'Origin':'https://testserver'},json={'version':state['version'],'clocks':state['default_clocks']})
    assert reset.status_code==200
    ordered=reset.json()['settings']['clocks'][1:][::-1]
    result=c.patch('/dashboard/settings',headers={'Origin':'https://testserver'},json={'version':reset.json()['version'],'clocks':ordered})
    assert result.status_code==200
    assert c.get('/dashboard/settings').json()['settings']['clocks']==ordered
    login(c)
    assert c.get('/dashboard/settings').json()['settings']['clocks']==before
    change(c,'/administration/users',dict(username='clockviewer',password='test-password',roles=['User']))
    login(c,'clockviewer','test-password')
    state=c.get('/dashboard/settings').json()
    assert c.patch('/dashboard/settings',headers={'Origin':'https://testserver'},json={'version':state['version'],'clocks':state['default_clocks']}).status_code==403
