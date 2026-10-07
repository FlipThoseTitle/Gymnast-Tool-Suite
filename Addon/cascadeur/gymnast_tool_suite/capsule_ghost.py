# original script by Sonamenil

from . import capsule

def command_name():
    return 'Gymnast Tool Suite.Capsules.Connect Capsules to AutoPhysics Ghost'

def command_description():
    return 'Connect existing live capsules to the Autophysics Ghost.'

def run(scene):
    try:
        count=capsule.attach_existing(scene)
        scene.success('Connected '+str(count)+' Capsule Mesh Parts to the AutoPhysics Ghost.')
    except Exception as exc:
        scene.error('Live Capsule: '+str(exc))
